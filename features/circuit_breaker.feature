@rnf @resiliencia @disponibilidade
Feature: Circuit Breaker no serviço de pagamentos do Nubank
  Como sistema resiliente do Nubank
  Quero proteger o serviço de pagamentos contra falhas do gateway BACEN
  Para manter disponibilidade de 99.9% mesmo com instabilidades externas

  @sucesso
  Scenario: Requisições passam normalmente com CB fechado
    Given o gateway do BACEN está operando normalmente
    And o circuit breaker está no estado "CLOSED"
    When processo 5 transferências PIX consecutivas
    Then todas as 5 transferências são aprovadas
    And o circuit breaker permanece no estado "CLOSED"

  @borda
  Scenario: CB em HALF-OPEN testa recuperação do gateway
    Given o circuit breaker está no estado "OPEN" há 30 segundos
    And o gateway do BACEN voltou a responder
    When o tempo de reset do circuit breaker expira
    Then o circuit breaker muda para o estado "HALF-OPEN"
    And uma requisição de teste é enviada ao gateway
    And a requisição de teste é aprovada
    And o circuit breaker retorna para o estado "CLOSED"

  @falha
  Scenario: CB abre após 3 falhas consecutivas e ativa fallback
    Given o gateway do BACEN está instável
    And o circuit breaker está no estado "CLOSED"
    When ocorrem 3 timeouts consecutivos no gateway
    Then o circuit breaker muda para o estado "OPEN"
    And novas requisições são respondidas com fallback
    And o fallback retorna mensagem "servico_temporariamente_indisponivel"
