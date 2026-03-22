"""
Steps para RNF1: Circuit Breaker no serviço de pagamentos (Nubank)
Mocks simulam estados do CB (CLOSED, OPEN, HALF-OPEN) e falhas reais do gateway.
"""

from behave import given, when, then
from unittest.mock import MagicMock


# ──────────────────────────────────────────────
# Classe auxiliar — Circuit Breaker simplificado
# ──────────────────────────────────────────────

class CircuitBreaker:
    """Implementação mínima de CB para fins de teste BDD."""

    def __init__(self, limite_falhas=3, reset_timeout_s=30):
        self.estado = "CLOSED"
        self.falhas_consecutivas = 0
        self.limite_falhas = limite_falhas
        self.reset_timeout_s = reset_timeout_s
        self.tempo_abertura = None

    def registrar_falha(self):
        self.falhas_consecutivas += 1
        if self.falhas_consecutivas >= self.limite_falhas:
            self.estado = "OPEN"

    def registrar_sucesso(self):
        self.falhas_consecutivas = 0
        self.estado = "CLOSED"

    def tentar_recuperacao(self):
        self.estado = "HALF-OPEN"

    def executar(self, gateway, **kwargs):
        if self.estado == "OPEN":
            return {"status": "fallback", "mensagem": "servico_temporariamente_indisponivel"}

        try:
            resultado = gateway.transferir_pix(**kwargs)
            self.registrar_sucesso()
            return resultado
        except (TimeoutError, ConnectionError):
            self.registrar_falha()
            if self.estado == "OPEN":
                return {"status": "fallback", "mensagem": "servico_temporariamente_indisponivel"}
            raise


# ──────────────────────────────────────────────
# GIVEN steps — Cenário de sucesso (CB fechado)
# ──────────────────────────────────────────────

@given("o gateway do BACEN está operando normalmente")
def step_gateway_normal(context):
    context.gateway = MagicMock()
    context.gateway.transferir_pix.return_value = {
        "status": "aprovado",
        "transacao_id": "E00000000-2026-0322-1500-NORMAL00001",
        "tempo_ms": 800,
    }


@given('o circuit breaker está no estado "{estado}"')
def step_cb_estado(context, estado):
    context.cb = CircuitBreaker(limite_falhas=3, reset_timeout_s=30)
    context.cb.estado = estado


# ──────────────────────────────────────────────
# GIVEN steps — Cenário de borda (HALF-OPEN)
# ──────────────────────────────────────────────

@given('o circuit breaker está no estado "OPEN" há 30 segundos')
def step_cb_open_timeout(context):
    context.cb = CircuitBreaker(limite_falhas=3, reset_timeout_s=30)
    context.cb.estado = "OPEN"
    context.cb.tempo_abertura = -30  # Simula que já passou o reset_timeout


@given("o gateway do BACEN voltou a responder")
def step_gateway_recuperado(context):
    context.gateway = MagicMock()
    context.gateway.transferir_pix.return_value = {
        "status": "aprovado",
        "transacao_id": "E00000000-2026-0322-1530-RECOV000001",
        "tempo_ms": 950,
    }


# ──────────────────────────────────────────────
# GIVEN steps — Cenário de falha (CB abre)
# ──────────────────────────────────────────────

@given("o gateway do BACEN está instável")
def step_gateway_instavel(context):
    context.gateway = MagicMock()
    context.gateway.transferir_pix.side_effect = [
        TimeoutError("BACEN SPI timeout: 10s exceeded"),
        TimeoutError("BACEN SPI timeout: 10s exceeded"),
        TimeoutError("BACEN SPI timeout: 10s exceeded"),
        {"status": "aprovado", "transacao_id": "E-RECOVERY", "tempo_ms": 500},
    ]


# ──────────────────────────────────────────────
# WHEN steps
# ──────────────────────────────────────────────

@when("processo {n:d} transferências PIX consecutivas")
def step_processar_n_pix(context, n):
    context.resultados = []
    for i in range(n):
        resultado = context.cb.executar(
            context.gateway, valor=100.00, chave_destino=f"chave_{i}"
        )
        context.resultados.append(resultado)


@when("o tempo de reset do circuit breaker expira")
def step_reset_expira(context):
    context.cb.tentar_recuperacao()
    # Guarda o estado intermediário antes de enviar a requisição de teste
    context.estado_apos_reset = context.cb.estado


@when("ocorrem {n:d} timeouts consecutivos no gateway")
def step_timeouts_consecutivos(context, n):
    context.falhas = 0
    for _ in range(n):
        try:
            context.cb.executar(
                context.gateway, valor=100.00, chave_destino="chave_qualquer"
            )
        except TimeoutError:
            context.falhas += 1


# ──────────────────────────────────────────────
# THEN steps — Cenário de sucesso
# ──────────────────────────────────────────────

@then("todas as {n:d} transferências são aprovadas")
def step_todas_aprovadas(context, n):
    assert len(context.resultados) == n, (
        f"Esperado {n} resultados, obtido {len(context.resultados)}"
    )
    for i, resultado in enumerate(context.resultados):
        assert resultado["status"] == "aprovado", (
            f"Transferência {i+1} deveria ser 'aprovado', obtido '{resultado['status']}'"
        )


@then('o circuit breaker permanece no estado "{estado}"')
def step_cb_permanece(context, estado):
    assert context.cb.estado == estado, (
        f"CB deveria estar '{estado}', está '{context.cb.estado}'"
    )


# ──────────────────────────────────────────────
# THEN steps — Cenário de borda (HALF-OPEN)
# ──────────────────────────────────────────────

@then('o circuit breaker muda para o estado "{estado}"')
def step_cb_muda_estado(context, estado):
    assert context.cb.estado == estado, (
        f"CB deveria estar '{estado}', está '{context.cb.estado}'"
    )


@then("uma requisição de teste é enviada ao gateway")
def step_req_teste_enviada(context):
    # Envia a requisição de teste agora (em HALF-OPEN)
    context.resultado_teste = context.cb.executar(
        context.gateway, valor=1.00, chave_destino="teste_health_check"
    )
    context.gateway.transferir_pix.assert_called()


@then("a requisição de teste é aprovada")
def step_req_teste_aprovada(context):
    assert context.resultado_teste is not None
    assert context.resultado_teste["status"] == "aprovado", (
        f"Requisição de teste deveria ser aprovada, obtido: {context.resultado_teste['status']}"
    )


@then('o circuit breaker retorna para o estado "CLOSED"')
def step_cb_retorna_closed(context):
    assert context.cb.estado == "CLOSED", (
        f"CB deveria ter retornado para CLOSED, está '{context.cb.estado}'"
    )


# ──────────────────────────────────────────────
# THEN steps — Cenário de falha (CB abre)
# ──────────────────────────────────────────────

@then("novas requisições são respondidas com fallback")
def step_fallback_ativo(context):
    resultado = context.cb.executar(
        context.gateway, valor=50.00, chave_destino="chave_pos_abertura"
    )
    assert resultado["status"] == "fallback", (
        f"Com CB OPEN, deveria retornar fallback, obtido: {resultado['status']}"
    )
    context.resultado_fallback = resultado


@then('o fallback retorna mensagem "{mensagem}"')
def step_fallback_mensagem(context, mensagem):
    resultado = context.cb.executar(
        context.gateway, valor=50.00, chave_destino="chave_verificacao"
    )
    assert resultado["mensagem"] == mensagem, (
        f"Mensagem de fallback esperada '{mensagem}', obtida '{resultado['mensagem']}'"
    )
