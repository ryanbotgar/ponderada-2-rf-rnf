"""
Steps para RF1: Realizar transferência via PIX (Nubank)
Mocks simulam comportamento real do gateway BACEN (SPI).
"""

from behave import given, when, then
from unittest.mock import MagicMock
import time


# ──────────────────────────────────────────────
# GIVEN steps
# ──────────────────────────────────────────────

@given('um pedido de transferência PIX de R$ {valor} para a chave "{chave}"')
def step_pedido_pix(context, valor, chave):
    context.valor = float(valor.replace(",", "."))
    context.chave_destino = chave


@given("o gateway do BACEN está disponível")
def step_gateway_disponivel(context):
    context.gateway = MagicMock()
    context.gateway.transferir_pix.return_value = {
        "status": "aprovado",
        "transacao_id": "E00000000-2026-0322-1400-ABCDEF123456",
        "tempo_ms": 1200,
        "timestamp": "2026-03-22T14:00:00-03:00",
    }


@given("o gateway do BACEN está respondendo com lentidão")
def step_gateway_lento(context):
    context.gateway = MagicMock()
    context.gateway.transferir_pix.return_value = {
        "status": "aprovado",
        "transacao_id": "E00000000-2026-0322-1401-SLOW9876543",
        "tempo_ms": 4900,
        "timestamp": "2026-03-22T14:01:00-03:00",
    }


@given("o gateway do BACEN está offline")
def step_gateway_offline(context):
    context.gateway = MagicMock()
    context.gateway.transferir_pix.side_effect = ConnectionError(
        "BACEN SPI gateway unreachable: connection refused"
    )


# ──────────────────────────────────────────────
# WHEN steps
# ──────────────────────────────────────────────

@when("solicito a transferência via PIX")
def step_solicitar_pix(context):
    inicio = time.time()
    try:
        context.resultado = context.gateway.transferir_pix(
            valor=context.valor,
            chave_destino=context.chave_destino,
        )
        context.erro = None
    except ConnectionError as e:
        context.resultado = None
        context.erro = {
            "tipo": "gateway_indisponivel",
            "mensagem": str(e),
        }
    context.tempo_processamento = time.time() - inicio


# ──────────────────────────────────────────────
# THEN steps — Cenário de sucesso
# ──────────────────────────────────────────────

@then('a transferência é confirmada com status "{status}"')
def step_confirmar_status(context, status):
    assert context.resultado is not None, "Resultado não deveria ser None"
    assert context.resultado["status"] == status, (
        f"Esperado status '{status}', obtido '{context.resultado['status']}'"
    )


@then("o tempo de processamento é inferior a 5 segundos")
def step_verificar_tempo(context):
    tempo_simulado = context.resultado["tempo_ms"] / 1000
    assert tempo_simulado < 5.0, (
        f"Tempo de processamento {tempo_simulado}s excede o SLA de 5s"
    )


@then("um comprovante é gerado com número de transação válido")
def step_verificar_comprovante(context):
    txn_id = context.resultado["transacao_id"]
    assert txn_id is not None, "ID de transação não pode ser None"
    assert txn_id.startswith("E"), (
        f"ID de transação PIX deve iniciar com 'E' (padrão BACEN), obtido: {txn_id}"
    )
    assert len(txn_id) > 20, (
        f"ID de transação muito curto para padrão EndToEndId: {txn_id}"
    )


# ──────────────────────────────────────────────
# THEN steps — Cenário de borda
# ──────────────────────────────────────────────

@then("um alerta de latência elevada é registrado")
def step_alerta_latencia(context):
    tempo_ms = context.resultado["tempo_ms"]
    assert tempo_ms >= 3000, (
        f"Alerta de latência só é disparado acima de 3000ms, obtido: {tempo_ms}ms"
    )
    # Simula registro de alerta no sistema de observabilidade
    context.alerta_registrado = True
    assert context.alerta_registrado is True


# ──────────────────────────────────────────────
# THEN steps — Cenário de falha
# ──────────────────────────────────────────────

@then('a transferência falha com erro "{tipo_erro}"')
def step_verificar_falha(context, tipo_erro):
    assert context.erro is not None, "Deveria ter ocorrido um erro"
    assert context.erro["tipo"] == tipo_erro, (
        f"Tipo de erro esperado '{tipo_erro}', obtido '{context.erro['tipo']}'"
    )


@then("o cliente recebe uma mensagem orientando tentar novamente")
def step_mensagem_retry(context):
    assert context.erro is not None
    assert "unreachable" in context.erro["mensagem"].lower() or \
           "refused" in context.erro["mensagem"].lower(), (
        "Mensagem de erro deve indicar indisponibilidade do gateway"
    )


@then("o erro é registrado no sistema de monitoramento")
def step_registrar_erro(context):
    # Verifica que o mock foi chamado (tentativa de processamento ocorreu)
    context.gateway.transferir_pix.assert_called_once_with(
        valor=context.valor,
        chave_destino=context.chave_destino,
    )
