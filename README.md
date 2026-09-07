# BB84 Quantum Key Distribution (QKD) Simulation

A Qiskit-based simulation and analysis of the **BB84 Quantum Key Distribution (QKD)** protocol.

This project implements the complete BB84 workflow, including quantum state preparation, transmission, eavesdropping, channel imperfections, basis reconciliation, key sifting, parameter estimation, QBER-based abort decisions, error reconciliation, privacy amplification, and final secret-key generation.

The project focuses on analyzing how **eavesdropping and quantum-channel imperfections affect QBER, security decisions, and the final secret-key rate**.

---

## Project Overview

Quantum Key Distribution (QKD) enables two parties, **Alice and Bob**, to establish a shared secret key over a quantum channel while detecting disturbances that may indicate eavesdropping.

This project implements BB84 using **Qiskit** for quantum state preparation and measurement, with **Python and NumPy** used for classical processing and experimental analysis.

The simulation covers:

* BB84 quantum state preparation and measurement
* Random basis selection
* Basis reconciliation and key sifting
* Quantum Bit Error Rate (QBER) estimation
* Intercept-resend eavesdropping
* Photon loss
* Simplified quantum-channel bit-flip noise
* Simplified detector dark-count errors
* Parameter estimation
* QBER-based abort decisions
* Parity-based error reconciliation
* Reconciliation leakage tracking
* Toeplitz-matrix privacy amplification
* Final secret-key generation
* Key-rate analysis
* Eve and channel-noise experiments
* Finite-key statistical analysis
* Comparison with theoretical BB84 behavior

---

# Protocol Workflow

The complete simulated QKD pipeline is:

```text
Alice
  │
  ├── Random Bits & Bases
  │
  ▼
Quantum State Preparation
  │
  ▼
Quantum Channel
  │
  ├── Photon Loss
  ├── Channel Noise
  └── Eve (Optional)
  │
  ▼
Bob's Measurement
  │
  ▼
Basis Reconciliation
  │
  ▼
Key Sifting
  │
  ▼
Parameter Estimation
  │
  ▼
QBER Calculation
  │
  ▼
Abort Decision
  │
  ├── QBER > Threshold → ABORT
  │
  ▼
Error Reconciliation
  │
  ▼
Privacy Amplification
  │
  ▼
Final Secret Key
```

The classical communication channel is assumed to be **authenticated**, while Eve may observe the public basis-reconciliation and post-processing communication.

---

# BB84 Protocol

## 1. Random Key and Basis Generation

Alice generates:

* A random binary key
* A random BB84 basis for each qubit

Bob independently generates a random measurement basis for every transmitted qubit.

The two BB84 bases are:

### Z Basis — Computational Basis

```text
Bit 0 → |0⟩
Bit 1 → |1⟩
```

### X Basis — Hadamard Basis

```text
Bit 0 → |+⟩
Bit 1 → |−⟩
```

The quantum states are prepared and measured using **Qiskit quantum circuits**.

---

# 2. Quantum State Preparation and Measurement

The implementation uses Qiskit to model the actual BB84 quantum operations.

For the Z basis:

```text
0 → |0⟩
1 → X|0⟩ = |1⟩
```

For the X basis:

```text
0 → H|0⟩ = |+⟩
1 → HX|0⟩ = |−⟩
```

Bob applies the appropriate measurement basis before measuring the received qubit.

This allows the project to combine a **quantum-circuit implementation** with classical simulation and analysis.

---

# 3. Quantum Channel

The quantum channel models imperfections that can occur during transmission.

The current simulation includes:

### Photon Loss

Controlled by:

```python
p_loss
```

A transmitted qubit may be lost before reaching Bob.

Loss reduces the number of usable detected qubits but does not directly represent a bit error.

### Simplified Bit-Flip Noise

Controlled by:

```python
p_depolarizing
```

> **Note:** The current implementation uses this parameter as a simplified **bit-flip error probability**, not a full physical depolarizing channel.

When the noise event occurs, an `X` operation is applied to the qubit.

This simplified model is intentionally used for the current simulation and analysis.

### Dark-Count Model

A simplified measurement-error model is also included through:

```python
p_dark_counts
```

This can randomly flip Bob's measured bit to model detector-related errors.

---

# 4. Eavesdropping Model

The project implements an **Intercept-Resend attack**.

For every qubit intercepted by Eve:

1. Eve randomly selects a measurement basis.
2. Eve measures the qubit.
3. Eve obtains a classical bit.
4. Eve prepares a new qubit using her measurement result.
5. Eve sends the new qubit to Bob.

The interception probability is controlled by:

```python
p_eve
```

where:

```text
p_eve = 0.0 → Eve does not intercept
p_eve = 1.0 → Eve intercepts every qubit
```

For an ideal BB84 channel with intercept-resend eavesdropping, the expected QBER contribution is approximately:

```text
QBER ≈ 0.25 × p_eve
```

Therefore:

```text
p_eve = 0.0 → ≈ 0% QBER contribution
p_eve = 0.5 → ≈ 12.5%
p_eve = 1.0 → ≈ 25%
```

The 25% value is the theoretical benchmark for the **ideal Eve-only case**.

When channel noise is also enabled, the measured QBER represents the combined effect of channel imperfections and Eve.

---

# 5. Basis Reconciliation and Key Sifting

After quantum transmission, Alice and Bob publicly compare their measurement bases.

They keep only the positions where:

```text
Alice Basis == Bob Basis
```

Lost qubits are also excluded.

The resulting bits form the **sifted key**.

For independently random BB84 bases, the expected sifting efficiency is:

```text
≈ 50%
```

The implementation records the number of transmitted and sifted bits and calculates the corresponding sifting efficiency.

---

# 6. Parameter Estimation

Before generating the final secret key, Alice and Bob use a randomly selected portion of the sifted key to estimate the channel error rate.

The process is:

```text
Sifted Key
    │
    ▼
Random Estimation Sample
    │
    ▼
QBER Estimation
    │
    ▼
Threshold Comparison
```

The sampled bits are removed from the remaining key material and are not used directly for the final secret key.

The remaining bits are used for reconciliation and privacy amplification.

The current implementation uses:

```python
ESTIMATION_FRACTION = 0.25
```

meaning approximately 25% of the sifted key is used for parameter estimation.

---

# 7. QBER

The **Quantum Bit Error Rate (QBER)** is calculated as:

```text
QBER = Number of mismatched bits
       ─────────────────────────
       Number of tested bits
```

QBER can increase because of:

* Channel noise
* Photon-related imperfections
* Detector errors
* Eavesdropping
* A combination of these effects

For an ideal BB84 reference case with no Eve and no channel noise:

```text
QBER ≈ 0%
```

A non-zero QBER therefore does **not automatically prove that Eve is present**.

---

# 8. Abort Decision

The estimated QBER is compared against a predefined threshold.

The current implementation uses:

```python
Q_THRESHOLD = 0.11
```

The decision process is:

```text
QBER ≤ 11%
      │
      ▼
   Continue
      │
      ▼
Reconciliation
      │
      ▼
Privacy Amplification
      │
      ▼
Final Key
```

If:

```text
QBER > 11%
```

the protocol aborts and no final secret key is generated.

The approximately 11% value is used as an **asymptotic BB84 security benchmark under idealized assumptions**. It is not a universal threshold for every practical QKD implementation.

Real security limits depend on factors such as:

* Error-correction efficiency
* Finite-key effects
* Source imperfections
* Detector behavior
* Security model
* Implementation assumptions

The threshold is applied to the **total observed QBER**, including both channel noise and potential eavesdropping.

---

# 9. Error Reconciliation

After parameter estimation, Alice and Bob need to correct discrepancies between their remaining keys.

The project implements a **simplified parity-based reconciliation algorithm**.

The main functions include:

```python
block_parity(bits)
```

```python
binary_search_correct(...)
```

```python
reconcile_keys(...)
```

The current approach:

1. Divides the key into blocks.
2. Calculates the parity of each block.
3. Compares Alice's and Bob's parity.
4. Identifies blocks with different parity.
5. Uses binary search to locate a single-bit error.
6. Corrects the detected error.
7. Tracks the information revealed during reconciliation.

The amount of information revealed during error correction is tracked using:

```text
leak_EC
```

### Important Note

This is a **simplified reconciliation model**, not a complete implementation of the practical Cascade protocol.

In particular, the current implementation uses a single block-parity pass. Multiple errors inside the same block may cancel each other in the parity calculation and remain undetected.

The simplified implementation is sufficient for demonstrating the main QKD post-processing concept within this simulation.

---

# 10. Privacy Amplification

Even after reconciliation, Eve may potentially possess partial information about the reconciled key.

Privacy amplification reduces this potential information by compressing the key.

The project uses **Toeplitz-matrix universal hashing**.

The process is:

```text
Reconciled Key
      │
      ▼
Estimate Information Leakage
      │
      ▼
Calculate Final Key Length
      │
      ▼
Generate Toeplitz Matrix
      │
      ▼
Universal Hashing
      │
      ▼
Final Secret Key
```

The main functions are:

```python
binary_entropy(qber)
```

```python
choose_final_key_length(...)
```

```python
generate_toeplitz_matrix(m, n)
```

```python
apply_toeplitz(T, key_bits)
```

The final key length accounts for:

* Reconciliation leakage
* QBER-dependent information estimation
* A security margin

Conceptually:

```text
Higher QBER
     ↓
More estimated leakage
     ↓
Shorter final key
```

The current key-length calculation is a **simulation-oriented asymptotic heuristic** and should not be interpreted as a complete composable finite-key security proof.

---

# 11. Key-Rate Analysis

The project analyzes the relationship between QBER and the final secret-key rate.

Two useful quantities are considered conceptually:

### Key Rate per Transmitted Qubit

```text
R_sent = Final Key Length / Number of Sent Qubits
```

### Key Rate per Sifted/Usable Key Bit

```text
R_sifted = Final Key Length / Number of Sifted Key Bits
```

The distinction is important because BB84 naturally loses approximately half of the transmitted bits during basis sifting.

Theoretical BB84 behavior is also used as a benchmark:

```text
r_theory ≈ 1 − 2h₂(Q)
```

where `h₂(Q)` is the binary entropy function.

The theoretical expression represents an idealized asymptotic benchmark, while the simulated key rate additionally reflects:

* Sifting
* Parameter estimation
* Reconciliation leakage
* Security margin
* Channel imperfections

---

# 12. Experimental Scenarios

The simulation evaluates the system under multiple conditions.

## Scenario 1 — Ideal Reference

```text
Eve = OFF
Noise = OFF
Loss = OFF
```

Expected behavior:

```text
Sifting Efficiency ≈ 50%
QBER ≈ 0%
```

This validates the basic BB84 implementation.

---

## Scenario 2 — Channel Noise Only

```text
Eve = OFF
Channel Noise = ON
```

This experiment studies the effect of natural channel imperfections.

Expected behavior:

```text
Increasing Noise
       ↓
Increasing QBER
       ↓
Higher Estimated Leakage
       ↓
Lower Final Key Rate
       ↓
Possible Abort
```

This scenario demonstrates that a noisy channel can produce a non-zero QBER even when Eve is absent.

---

## Scenario 3 — Eve + Channel Noise

```text
Eve = ON
Channel Noise = ON
```

The Eve interception probability is varied while channel imperfections remain active.

Expected behavior:

```text
Channel Noise + Eve
        ↓
Higher QBER
        ↓
Higher Information Leakage
        ↓
Lower Final Key Rate
        ↓
Possible Abort
```

This experiment demonstrates the additional disturbance introduced by eavesdropping.

---

# 13. Finite-Key Analysis

The project also explores the effect of finite key sizes.

The simulation evaluates multiple key sizes and repeats the experiment over multiple trials.

The analysis focuses on:

* Mean QBER
* QBER standard deviation
* Abort probability
* Statistical fluctuations caused by finite sample sizes

This demonstrates an important difference between theoretical asymptotic results and practical finite-length QKD experiments.

The finite-key experiments are **experimental/statistical analysis**, not a formal finite-key security proof.

---

# 14. Main Experimental Outputs

The project generates several plots for analysis.

### QBER vs Eve Attack Strength

```text
qber_vs_attack_strength.png
```

This compares the simulated QBER against Eve's interception probability and the theoretical:

```text
QBER ≈ 0.25 × p_eve
```

---

### Final Key Rate vs QBER

```text
keyrate_vs_qber.png
```

This demonstrates the relationship between increasing QBER and decreasing secret-key generation capability.

---

### Eve × Noise Heatmap

```text
eve_noise_heatmap.png
```

This visualizes how QBER changes as both:

* Eve's interception probability
* Channel-noise probability

are varied.

---

### Finite-Key Sweep

```text
finite_key_sweep.png
```

This analyzes the statistical behavior of QBER and abort decisions for different key sizes.

---

# 15. Theoretical Benchmarks

The simulation is compared against the expected theoretical behavior of BB84.

| Quantity                              | Expected Behavior |
| ------------------------------------- | ----------------: |
| Random-basis sifting efficiency       |             ≈ 50% |
| Ideal QBER without Eve/noise          |              ≈ 0% |
| Full intercept-resend QBER            |             ≈ 25% |
| Partial intercept-resend contribution |   ≈ 25% × `p_eve` |
| Common asymptotic BB84 benchmark      |        ≈ 11% QBER |
| Ideal asymptotic secret fraction      |      `1 − 2h₂(Q)` |

The 25% intercept-resend benchmark applies to the **ideal Eve-only case**.

When channel noise is enabled, the experimentally observed QBER can be higher because it contains both:

```text
Channel Errors + Eve-Induced Errors
```

Therefore, the simulation should not be expected to produce exactly 25% QBER at full Eve interception when additional channel noise is enabled.

---

# 16. Security Assumptions

The current simulation uses the following assumptions:

* Ideal single-photon source
* Ideal quantum detectors
* Authenticated classical communication
* Prepare-and-measure BB84
* Simplified channel-noise model
* Simplified detector dark-count model
* Asymptotic security expressions as the primary theoretical reference
* Finite-key behavior explored experimentally
* No detector side-channel attacks modeled
* No photon-number-splitting attack modeled

These assumptions keep the project focused on the core BB84 security mechanism.

---

# 17. Security Discussion

## Finite-Key Effects

Theoretical BB84 security expressions are often derived under asymptotic assumptions.

For finite numbers of transmitted qubits, statistical fluctuations affect the estimated QBER and therefore the confidence of the security analysis.

The project explores this experimentally through different key sizes.

---

## Imperfect Photon Sources

Real QKD systems may use weak coherent pulses rather than ideal single-photon sources.

This can introduce additional security concerns, including photon-number-splitting attacks.

These effects are outside the current simulation scope.

---

## Detector Side Channels

Real QKD hardware can contain implementation-specific vulnerabilities in detectors and measurement devices.

Such side-channel attacks are not modeled in the current implementation.

---

## Reconciliation Limitations

The current error-reconciliation algorithm is intentionally simplified.

It demonstrates:

```text
Parity Checking
      ↓
Error Detection
      ↓
Binary Search
      ↓
Error Correction
      ↓
Leakage Tracking
```

but it is not a complete implementation of Cascade.

---

## Noise vs Eavesdropping

QBER alone cannot determine the exact source of observed errors.

Both:

```text
Channel Noise
```

and:

```text
Eavesdropping
```

can increase QBER.

Therefore, the project uses controlled experiments to study how Eve adds additional disturbance to an already noisy channel rather than claiming that every non-zero QBER proves Eve is present.

---

# 18. Implementation Status

| Feature                            |      Status     |
| ---------------------------------- | :-------------: |
| BB84 key exchange                  |    ✅ Complete   |
| Qiskit state preparation           |    ✅ Complete   |
| Qiskit measurement                 |    ✅ Complete   |
| Ideal-case validation              |    ✅ Complete   |
| Eve intercept-resend attack        |    ✅ Complete   |
| Photon-loss model                  |    ✅ Complete   |
| Simplified bit-flip channel noise  |    ✅ Complete   |
| Simplified dark-count model        |    ✅ Complete   |
| Basis reconciliation               |    ✅ Complete   |
| Key sifting                        |    ✅ Complete   |
| Parameter estimation               |    ✅ Complete   |
| QBER calculation                   |    ✅ Complete   |
| QBER-based abort decision          |    ✅ Complete   |
| Error reconciliation               |    ✅ Complete   |
| Reconciliation leakage tracking    |    ✅ Complete   |
| Toeplitz privacy amplification     |    ✅ Complete   |
| Final key generation               |    ✅ Complete   |
| QBER vs Eve analysis               |    ✅ Complete   |
| Eve × Noise analysis               |    ✅ Complete   |
| Final key-rate analysis            |    ✅ Complete   |
| Finite-key analysis                |    ✅ Complete   |
| Theoretical benchmarking           |    ✅ Complete   |
| Formal composable finite-key proof | ⚠️ Out of scope |
| Full Cascade implementation        | ⚠️ Out of scope |
| Full physical depolarizing channel | ⚠️ Out of scope |
| Hardware QKD implementation        | ⚠️ Out of scope |

---

# 19. Requirements

Install the required Python packages:

```bash
pip install qiskit qiskit-aer numpy scipy matplotlib
```

Python 3.9+ is recommended.

---

# 20. How to Run

Run the main Python simulation:

```bash
python <your_main_file>.py
```

The program runs the BB84 experiments and generates the corresponding analysis plots.

The main outputs include:

```text
qber_vs_attack_strength.png
keyrate_vs_qber.png
eve_noise_heatmap.png
finite_key_sweep.png
```

---

# 21. Expected Results

The simulation should reproduce the following general behavior:

| Quantity                    | Expected Behavior         |
| --------------------------- | ------------------------- |
| Sifting efficiency          | ≈ 50%                     |
| Ideal reference QBER        | ≈ 0%                      |
| Channel noise               | QBER increases            |
| Noise without Eve           | Non-zero QBER is possible |
| Adding Eve                  | QBER increases further    |
| Full ideal intercept-resend | ≈ 25% QBER                |
| Increasing QBER             | Final key rate decreases  |
| High QBER                   | Final key becomes shorter |
| QBER above threshold        | Protocol aborts           |

The central relationship is:

```text
More Noise / More Eve
        ↓
      Higher QBER
        ↓
 More Information Leakage
        ↓
   Shorter Final Key
        ↓
    Possible Abort
```

---

# 22. Project Goals

The main goals of this project are to:

1. Implement the BB84 QKD protocol using Qiskit.
2. Demonstrate how basis reconciliation produces the sifted key.
3. Measure QBER under ideal, noisy, and eavesdropped conditions.
4. Demonstrate the security impact of an intercept-resend attack.
5. Distinguish channel noise from additional eavesdropping disturbance.
6. Implement simplified error reconciliation.
7. Apply Toeplitz-based privacy amplification.
8. Analyze final secret-key generation and key rates.
9. Explore finite-key statistical effects.
10. Compare experimental behavior with theoretical BB84 benchmarks.

---

# 23. Conclusion

This project demonstrates an end-to-end simulation of **BB84 Quantum Key Distribution**, from quantum state preparation and transmission to final secret-key generation.

The experiments show the fundamental security behavior of BB84:

```text
Quantum Channel
      ↓
Measurement
      ↓
QBER Estimation
      ↓
Security Decision
      ↓
Error Reconciliation
      ↓
Privacy Amplification
      ↓
Final Secret Key
```

The simulation demonstrates that:

* BB84 produces approximately 50% sifting efficiency under random basis selection.
* An ideal channel produces approximately 0% QBER.
* Intercept-resend eavesdropping introduces measurable errors.
* Full intercept-resend produces approximately 25% QBER in the ideal Eve-only case.
* Channel noise can also increase QBER without an attacker.
* Increasing QBER reduces the amount of extractable secret key.
* Excessive QBER causes the protocol to abort.
* Privacy amplification reduces the potential information available to an adversary.

The project therefore provides a practical simulation-based demonstration of the core security principles behind **Quantum Key Distribution and BB84**.

---

# 24. Team

### Team QRYPTQ

**Alexandria Quantum Hackathon 2026**

Track: **Securing the Quantum Channel — Quantum Key Distribution (QKD)**

---
