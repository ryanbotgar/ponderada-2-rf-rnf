# Ponderada 2 — RF e RNF como Código

**Empresa Digital:** Nubank  
**Aspecto arquitetural:** Integração com o sistema de pagamentos instantâneos (PIX) via BACEN  
**Aluno:** Ryan  
**Módulo:** ES09 — Engenharia de Software | Inteli

---

## Contexto

O Nubank processa milhões de transações PIX diariamente. A arquitetura do serviço de pagamentos precisa garantir processamento rápido e resiliência contra falhas do gateway do BACEN. Este projeto modela um requisito funcional (transferência PIX) e um requisito não funcional (disponibilidade via Circuit Breaker) como código executável usando BDD com Behave.

**Arquitetura simplificada:**

```
App Nubank → Serviço de Pagamentos → Gateway BACEN (PIX)
```

---

## Mapeamento RF/RNF

| Requisito | Tipo | Tática | Mecanismo | Justificativa | Massa de Testes |
|---|---|---|---|---|---|
| RF1: Realizar transferência PIX em até 5s | RF | N/A | Gateway API BACEN (SPI) | O PIX exige confirmação em tempo real; o SLA do BACEN define limite de 10s, mas a UX do Nubank exige resposta em até 5s | Feliz: PIX aprovado em 1.2s / Borda: PIX aprovado em 4.9s (limite) / Falha: gateway offline (ConnectionError) |
| RNF1: Disponibilidade 99.9% do serviço de pagamentos | RNF | Circuit Breaker | Biblioteca de resiliência (ex: pybreaker/Hystrix) com estados CLOSED→OPEN→HALF-OPEN | O Circuit Breaker isola falhas do gateway externo, evitando cascata e mantendo o serviço respondendo com fallback enquanto o BACEN estiver instável | Feliz: CB fechado, requisições passam normalmente / Borda: CB em HALF-OPEN testa recuperação / Falha: 3 timeouts consecutivos abrem o CB |

---

## Estrutura do Projeto

```
Ponderada 2/
├── README.md
├── requirements.txt
└── features/
    ├── transferencia_pix.feature         # RF1 — BDD Feature
    ├── circuit_breaker.feature           # RNF1 — BDD Feature
    └── steps/
        ├── transferencia_pix_steps.py    # Steps + Mocks do RF1
        └── circuit_breaker_steps.py      # Steps + Mocks do RNF1
```

---

## Como Executar

```bash
pip install behave
behave
```

---

## Referências

- [Behave Documentation](https://behave.readthedocs.io)
- [BACEN — Regulamento do PIX](https://www.bcb.gov.br/estabilidadefinanceira/pix)
- Pressman — Engenharia de Software (RNFs verificáveis)
- ISO/IEC 25010 — Modelo de qualidade de produto de software
