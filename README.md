# BB84 QKD Simulation

A Qiskit-based simulation of the **BB84 Quantum Key Distribution (QKD)** protocol.

The project demonstrates the complete QKD workflow, from quantum key exchange and basis reconciliation to eavesdropping detection, error reconciliation, and privacy amplification.

The main goal is to study how **quantum-channel noise and eavesdropping affect QBER and the final secret-key generation process**.

---

# Project Overview

Quantum Key Distribution allows two parties, **Alice and Bob**, to establish a shared secret key over a quantum channel while detecting potential eavesdropping.

This project implements and analyzes the BB84 protocol using **Qiskit**, with classical post-processing using Python, NumPy, and related tools.

The simulation focuses on:

* BB84 quantum state preparation and measurement
* Basis reconciliation and key sifting
* Quantum Bit Error Rate (QBER) calculation
* Quantum-channel noise
* Intercept-resend eavesdropping
* Error reconciliation
* Privacy amplification
* QBER-based abort decisions
* Final secret-key rate analysis
* Comparison with theoretical BB84 behavior

---

# Protocol Workflow

The simulated QKD pipeline follows:

<div align="center">

<pre>
Alice
  ↓
Random Bits and Bases
  ↓
Quantum State Preparation
  ↓
Quantum Channel
  ↓
Eve (Optional)
  ↓
Bob's Measurement
  ↓
Basis Reconciliation
  ↓
Key Sifting
  ↓
Parameter Estimation
  ↓
QBER Calculation
  ↓
Abort Decision
  ↓
Error Reconciliation
  ↓
Privacy Amplification
  ↓
Final Secret Key
</pre>

</div>

---

# Project Structure

```text
.
├── refactor will be after finishing the code
├──
├──
├── README.md
```

### `file1.py`

Implements the core BB84 key-exchange pipeline and validates the ideal case (this is an example).

### `test.py`

Extends the basic implementation with:

* Eve intercept-resend attack
* Channel-noise experiments
* QBER analysis
* Error reconciliation
* Privacy amplification
* Experimental analysis

---

# Requirements

Install the required Python packages:

```bash
pip install qiskit qiskit-aer numpy scipy matplotlib
```

---

# 1. BB84 Key Exchange

Alice generates:

* A random binary key
* A random basis for each bit

The two BB84 bases are:

* **Z basis**: computational basis
* **X basis**: Hadamard basis

The states are prepared as follows:

**Z basis:** **Bit 0 → |0⟩**    **Bit 1 → |1⟩**

**X basis:** **Bit 0 → |+⟩**    **Bit 1 → |−⟩**

Bob independently chooses a random measurement basis for every received qubit.

The main exchange function is:

```python
run_bb84_exchange(n_qubits, p_eve=0.0)
```

The simulation stores:

* Alice's bits
* Alice's bases
* Bob's bases
* Bob's measurement results
* Eve's interception information when an attack is enabled

---

# 2. Basis Reconciliation and Key Sifting

After quantum transmission, Alice and Bob publicly compare their bases.

They keep only the positions where their bases match.

```python
sift_keys(...)
```

For randomly selected BB84 bases, approximately half of the transmitted bits are expected to survive.

### Expected behavior

```text
Sifting efficiency ≈ 50%
```

Sifting efficiency is mainly determined by the randomly chosen measurement bases and is expected to remain approximately 50% in both experimental scenarios.

---

# 3. Quantum Bit Error Rate (QBER)

The **Quantum Bit Error Rate (QBER)** measures the fraction of mismatched bits in the sifted key.

It is calculated using:

```python
compute_qber(alice_sifted, bob_sifted)
```

QBER is a key indicator of the condition of the quantum channel.

A non-zero QBER can result from **channel noise, eavesdropping, or both**.

Therefore, the project does not assume that QBER must always be zero.

For an ideal reference case with no channel noise and no Eve:

```text
QBER ≈ 0%
```

However, in the main experiments, channel noise is enabled, so a non-zero QBER is expected even when Eve is disabled.

---

# 4. Eavesdropping Model

The project implements an **intercept-resend attack**.

For every qubit that Eve intercepts:

1. Eve randomly chooses a measurement basis.
2. Eve measures the qubit.
3. Eve obtains a classical bit.
4. Eve prepares a new qubit using her measurement result.
5. Eve sends the new qubit to Bob.

The probability of interception is controlled by:

```python
p_eve
```

where:

```text
p_eve = 0.0  → No interception
p_eve = 1.0  → Eve intercepts every qubit
```

The Eve attack is studied together with channel noise rather than as a separate experimental scenario.

---

# 5. Quantum Channel Noise

A channel-noise model is included to distinguish **natural channel errors** from additional disturbances caused by Eve.

The current model considers:

### Photon Loss

A qubit may be lost during transmission.

```python
p_loss
```

controls the probability of loss.

### Depolarizing Noise

Depolarizing noise introduces errors into the transmitted quantum state.

```python
p_depolarizing
```

controls the noise probability.

The noise model is represented by:

```python
apply_channel_noise(qc, p_loss, p_depolarizing)
```

The experiments use the channel-noise model as a baseline and then study the additional effect of Eve.

The two main scenarios are:

```text
Scenario 1:
No Eve + Channel Noise

Scenario 2:
Eve + Channel Noise
```

This allows the project to investigate how much additional QBER is introduced when eavesdropping is added to an already noisy quantum channel.

---

# 6. Parameter Estimation

Before producing the final secret key, Alice and Bob estimate the QBER using a sample of the sifted key.

The general process is:

```text
Sifted Key
    ↓
Random Sample
    ↓
Estimate QBER
    ↓
Compare with Threshold
```

The estimated QBER is used to determine whether the protocol can safely continue.

This step models the parameter-estimation stage used in practical QKD systems.

Because channel noise is present in the experiments, parameter estimation is important for determining whether the observed error rate is within the acceptable operating range.

---

# 7. Abort Decision

If the estimated QBER is too high, Alice and Bob should not continue generating a secret key.

The protocol follows:

<pre align="left">
 QBER ≤ Threshold
       ↓
    Continue
       ↓
 Reconciliation
       ↓
Privacy Amplification
       ↓
   Final Key
</pre>

while:

```text
QBER > Threshold
       ↓
     ABORT
       ↓
No final secret key
```

A commonly referenced BB84 benchmark is around **11% QBER** under standard assumptions for reconciliation and privacy amplification.

The threshold is treated as a security benchmark rather than a universal constant, since practical QKD security depends on the protocol assumptions, error-correction method, finite-key effects, and implementation details.

Importantly, the threshold is evaluated against the **total observed QBER**, which can contain contributions from both channel noise and Eve.

---

# 8. Error Reconciliation

Errors can occur in the sifted keys because of channel noise or eavesdropping.

The project implements a simplified parity-based reconciliation approach.

Main functions:

```python
block_parity(bits)
```

```python
binary_search_correct(...)
```

```python
reconcile_keys(alice_sifted, bob_sifted, block_size=8)
```

The process is:

1. Divide the key into blocks.
2. Calculate the parity of each block.
3. Compare Alice's and Bob's parity values.
4. Detect blocks with different parity.
5. Use binary search to locate a single-bit error.
6. Correct the detected error.
7. Track the amount of information revealed during reconciliation.

The leaked information is stored as:

```text
leak_EC
```

---

# 9. Privacy Amplification

Even after reconciliation, Eve may have partial information about the key.

Privacy amplification reduces this possible information by compressing the reconciled key.

The project uses **Toeplitz-matrix universal hashing**.

Main functions:

```python
binary_entropy(q)
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

The general process is:

```text
Reconciled Key
      ↓
Estimate Information Leakage
      ↓
Choose Shorter Key Length
      ↓
Toeplitz Universal Hashing
      ↓
Final Simulated Secret Key
```

In general:

```text
Higher QBER
      ↓
More estimated information leakage
      ↓
Shorter final key
```

The current key-length calculation is a **simulation heuristic** and should not be interpreted as a complete finite-key security proof.

---

# 10. Experimental Scenarios

The project evaluates **two main scenarios**.

---

## Scenario 1 — Channel Noise Without Eve

In this scenario, Eve is disabled while channel noise is enabled.

```text
Eve = OFF
Channel Noise = ON
```

The channel-noise probability is varied to study its effect on the QKD system.

Expected behavior:

```text
Increasing channel noise
          ↓
Increasing QBER
          ↓
Increasing information leakage
          ↓
Shorter final key
          ↓
Possible protocol abort
```

This scenario is important for analyzing **false-positive eavesdropping detection**.

A high QBER does not automatically prove that Eve is present, because normal channel noise can also introduce errors.

---

## Scenario 2 — Eve + Channel Noise

In this scenario, both Eve and channel noise are enabled.

```text
Eve = ON
Channel Noise = ON
```

The Eve interception probability is varied while the channel-noise model is also active.

Expected behavior:

```text
Channel Noise + Eve
        ↓
Additional quantum errors
        ↓
Higher QBER
        ↓
Higher estimated information leakage
        ↓
Lower final key rate
        ↓
Possible protocol abort
```

The experiment studies how the QBER and final secret-key rate change when eavesdropping is added to a noisy quantum channel.

---

# 11. Results and Analysis

The project evaluates the following metrics.

### Sifting Efficiency

The percentage of transmitted bits remaining after basis reconciliation.

Expected:

```text
≈ 50%
```

This should remain approximately 50% because Alice's and Bob's bases are chosen independently at random.

### QBER

QBER is measured for both experimental scenarios:

```text
Scenario 1:
No Eve + Channel Noise

Scenario 2:
Eve + Channel Noise
```

The comparison shows the additional disturbance caused by Eve on top of the existing channel noise.

### QBER vs Channel Noise

For Scenario 1, the channel-noise probability is varied.

Expected:

```text
Increasing channel noise
          ↓
Increasing QBER
```

This demonstrates that a noisy channel can produce a non-zero QBER even when no eavesdropper is present.

### QBER vs Eve Attack Probability

For Scenario 2, Eve's interception probability is varied while channel noise remains enabled.

The measured QBER is expected to increase as Eve intercepts more qubits.

For the ideal intercept-resend contribution alone:

```text
QBER ≈ 0.25 × p_eve
```

With channel noise also present, the total measured QBER is expected to be higher than the ideal Eve-only contribution.

### Final Key Rate

The project studies how the final key rate changes with increasing QBER.

Conceptually:

```text
QBER increases
      ↓
Security margin decreases
      ↓
Final key length decreases
```

If the estimated QBER exceeds the abort threshold:

```text
Protocol → ABORT
Final key → Not generated
```

---

# 12. Theoretical Benchmarking

The simulation results are compared with the expected theoretical behavior of BB84.

Important reference points include:

| Quantity                              | Theoretical Expectation |
| ------------------------------------- | ----------------------: |
| Random-basis sifting efficiency       |                   ≈ 50% |
| Ideal QBER without Eve/noise          |                    ≈ 0% |
| Full intercept-resend QBER            |                   ≈ 25% |
| Partial intercept-resend contribution |         ≈ 25% × `p_eve` |
| Common BB84 security benchmark        |              ≈ 11% QBER |

The **25% intercept-resend value applies to the ideal Eve-only case**.

Since the main experiments include channel noise, the experimentally observed QBER represents the combined effect of:

```text
Channel Noise + Eve-induced Errors
```

Therefore, the simulation should not be expected to produce exactly 25% QBER when `p_eve = 1` if channel noise is also enabled.

The purpose of the comparison is to verify that the simulation reproduces the qualitative security behavior predicted by BB84 theory.

---

# 13. Security Discussion

Although the simulation demonstrates the main BB84 security mechanism, a practical QKD system involves additional security considerations.

### Finite-Key Effects

The simulation uses finite numbers of qubits, while many theoretical security expressions are derived under asymptotic assumptions.

With a finite key, statistical fluctuations in the measured QBER must be considered.

### Imperfect Photon Sources

Real QKD systems may use weak coherent pulses rather than ideal single-photon sources.

This can introduce vulnerabilities such as photon-number-splitting attacks.

### Detector Side Channels

Real hardware may have implementation-specific vulnerabilities in detectors and measurement devices.

These side channels are outside the scope of the current simulation.

### Simplified Reconciliation

The current reconciliation algorithm is intentionally simpler than practical protocols such as Cascade.

### Noise vs Eavesdropping

An important limitation of the simulation is that QBER alone cannot identify the exact source of the errors.

Both channel noise and Eve can increase QBER.

The purpose of the two experimental scenarios is therefore to demonstrate the difference between:

```text
Natural Channel Errors
        vs
Channel Errors + Eavesdropping
```

rather than claiming that any non-zero QBER proves the presence of Eve.

---

# 14. Known Limitations

## Error Reconciliation

The current implementation uses a single block-parity pass.

If multiple errors occur in the same block, an even number of errors may cancel in the parity calculation and remain undetected.

More advanced protocols such as Cascade use multiple passes and different block arrangements.

This implementation therefore represents a simplified educational reconciliation model.

---

## Channel Noise

The channel-noise model is being integrated into the complete BB84 pipeline.

Until integration is complete, the noise function alone does not affect the main exchange results.

---

## Abort Logic

The protocol requires an explicit QBER-based abort decision.

The intended behavior is:

```text
QBER > threshold → ABORT
```

rather than simply generating a shorter key.

The threshold is applied to the total measured QBER, including errors caused by channel noise and potential eavesdropping.

---

## Privacy Amplification Security Model

The final key-length calculation is a simplified heuristic.

It demonstrates the relationship between:

```text
QBER
Leakage
Final Key Length
```

but it is not a complete finite-key security proof.

---

# 15. Implementation Status

| # | Feature | Status |
| :-: | :-------------------------------------------- | :------------------------------------ |
| 1 | BB84 key exchange | ✅ Complete |
| 2 | Ideal-case validation | ✅ Complete |
| 3 | Eve intercept-resend attack | ✅ Complete |
| 4 | Channel noise model | ⚠️ Implemented, integration in progress |
| 5 | Parameter estimation | ⚠️ In progress |
| 6 | QBER abort decision | ⚠️ In progress |
| 7 | Error reconciliation | ✅ Complete |
| 8 | Reconciliation leakage tracking | ✅ Complete |
| 9 | Privacy amplification | ✅ Complete |
| 10 | Scenario 1: Channel noise without Eve | ⚠️ In progress |
| 11 | Scenario 2: Channel noise + Eve | ⚠️ In progress |
| 12 | QBER vs channel noise | ⚠️ In progress |
| 13 | QBER vs Eve attack probability with channel noise | ⚠️ In progress |
| 14 | Final key rate vs QBER | ⚠️ In progress |
| 15 | Final key rate vs Eve + channel noise | ⚠️ In progress |
| 16 | Full theoretical benchmarking | ⚠️ Partial |

---

# 16. How to Run


---

# 17. Expected Behavior

The simulation should reproduce the following general behavior:

| Quantity | Expected Behavior |
| :------: | :---------------: |
| Sifting efficiency | ≈ 50% |
| Ideal reference QBER | ≈ 0% |
| Channel noise | QBER increases |
| Channel noise + no Eve | Non-zero QBER is possible |
| Adding Eve to noisy channel | QBER increases further |
| Full intercept-resend contribution | ≈ 25% in the ideal Eve-only case |
| Increasing QBER | Final key rate decreases |
| QBER above threshold | Protocol aborts |

The key distinction is:

```text
Scenario 1
Channel Noise
     ↓
Non-zero QBER possible
     ↓
No Eve

Scenario 2
Channel Noise + Eve
     ↓
Additional errors
     ↓
Higher QBER
     ↓
Possible ABORT
```

# 18. SDG Relevance

This project is primarily connected to:

### SDG 9 — Industry, Innovation and Infrastructure

QKD is a promising technology for future secure communication infrastructure and quantum-safe networking.

It also relates to:

### SDG 16 — Peace, Justice and Strong Institutions

Secure and tamper-evident communication can support trust in digital infrastructure, financial systems, institutions, and cross-border data exchange.
