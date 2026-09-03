# Web Agent Security Taxonomy

This taxonomy is a working scaffold for a future SoK-style corpus. It should evolve as new papers are added.

## 1. Observation / Environment Attacks

Attacks embedded in the environment observed by the agent.

- HTML/text injection
- Visual prompt injection
- Deceptive web interfaces
- Cross-application web manipulation

## 2. Context / Data Attacks

Attacks delivered through untrusted context that enters the agent's reasoning process.

- Indirect prompt injection
- Multi-source data injection
- Retrieval poisoning and reachability
- Tool-output injection

## 3. Tool / Action Attacks

Attacks against the tool and action-selection layer.

- Malicious tool descriptions
- Tool retrieval manipulation
- Unsafe tool invocation
- Action authorization failures

## 4. Resource / Availability Attacks

Attacks that degrade availability or inflate resource cost.

- Computational cost attacks
- Long-reasoning triggers
- Budget exhaustion
- Denial-of-wallet patterns

## 5. Privacy / Side Channels

Attacks that infer private information without necessarily changing the agent's explicit goal.

- Network metadata leakage
- Domain visitation leakage
- Timing side channels
- Prompt or trait inference

## 6. Defenses

Mechanisms that reduce compromise or unsafe action execution.

- Task alignment checks
- Masked re-execution
- Causal attribution
- Sandboxing and least privilege
- Human confirmation policies

## 7. Security Evaluation

Benchmarks and protocols for measuring Web Agent Security.

- Realistic web environments
- Adversarial trajectories
- Attack success rate
- Utility preservation
- Cost and latency impact
- Adaptive attack evaluation
