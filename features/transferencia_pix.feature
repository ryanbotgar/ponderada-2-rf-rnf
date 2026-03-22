@rf @pagamento @pix
Feature: Realizar transferência via PIX
  Como cliente do Nubank
  Quero realizar transferências via PIX em até 5 segundos
  Para ter uma experiência de pagamento instantâneo e confiável

  @sucesso
  Scenario: PIX processado com sucesso dentro do SLA
    Given um pedido de transferência PIX de R$ 250.00 para a chave "email@destino.com"
    And o gateway do BACEN está disponível
    When solicito a transferência via PIX
    Then a transferência é confirmada com status "aprovado"
    And o tempo de processamento é inferior a 5 segundos
    And um comprovante é gerado com número de transação válido

  @borda
  Scenario: PIX processado no limite do timeout de 5 segundos
    Given um pedido de transferência PIX de R$ 5000.00 para a chave "11999999999"
    And o gateway do BACEN está respondendo com lentidão
    When solicito a transferência via PIX
    Then a transferência é confirmada com status "aprovado"
    And o tempo de processamento é inferior a 5 segundos
    And um alerta de latência elevada é registrado

  @falha
  Scenario: Gateway do BACEN está offline
    Given um pedido de transferência PIX de R$ 100.00 para a chave "12345678900"
    And o gateway do BACEN está offline
    When solicito a transferência via PIX
    Then a transferência falha com erro "gateway_indisponivel"
    And o cliente recebe uma mensagem orientando tentar novamente
    And o erro é registrado no sistema de monitoramento
