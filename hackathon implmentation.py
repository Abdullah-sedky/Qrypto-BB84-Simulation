"""
BB84 Quantum Key Distribution (QKD) Simulation
==============================================
Alexandria Quantum Hackathon 2026
Team: QRYPTQ

Description
-----------
This module implements a complete simulation of the BB84 Quantum Key Distribution
protocol using Qiskit. It includes:

- Quantum state preparation and measurement
- Intercept-resend eavesdropping attack (Eve)
- Channel imperfections (photon loss, depolarizing noise, dark counts)
- Basis sifting
- Parameter estimation with sample splitting
- Abort decision based on estimated QBER
- Error reconciliation (parity + binary search)
- Privacy amplification using Toeplitz hashing
- Key rate estimation and experimental analysis

Security Assumptions
--------------------
- Ideal single-photon source (no multi-photon pulses → Photon-Number-Splitting
  attacks are not modelled)
- Ideal single-photon detectors (no detector side-channel attacks)
- Authenticated classical communication channel
- Asymptotic (large-key) security analysis is the primary model
- Finite-key effects are explored experimentally but not fully proven
- Simplified noise model (bit-flip channel)

Main Outputs
------------
- qber_vs_attack_strength.png
- keyrate_vs_qber.png
- eve_noise_heatmap.png
- finite_key_sweep.png
"""

import numpy as np
import secrets
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from scipy.linalg import toeplitz

# ============================================================
# GLOBAL CONFIGURATION
# ============================================================

simulator = AerSimulator()

# Abort threshold corresponding to the asymptotic BB84 security bound
# where the secret fraction r = 1 - 2*h2(Q) approaches zero (~11%)
Q_THRESHOLD = 0.11

# Fraction of the sifted key used for parameter estimation (QBER estimation).
# These bits are sacrificed and removed from the final key.
ESTIMATION_FRACTION = 0.25


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def secure_random_bits(n: int) -> np.ndarray:
    """
    Generate n cryptographically secure random bits.

    Parameters
    ----------
    n : int
        Number of random bits to generate. Must be positive.

    Returns
    -------
    np.ndarray
        Array of shape (n,) containing 0s and 1s.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")
    return np.array([secrets.randbits(1) for _ in range(n)], dtype=int)


def binary_entropy(q: float) -> float:
    """
    Compute the binary Shannon entropy h₂(q).

    h₂(q) = -q log₂(q) - (1-q) log₂(1-q)

    Parameters
    ----------
    q : float
        Probability value in [0, 1].

    Returns
    -------
    float
        Binary entropy value.
    """
    if q <= 0.0 or q >= 1.0:
        return 0.0
    return -q * np.log2(q) - (1.0 - q) * np.log2(1.0 - q)


def asymptotic_secret_fraction(qber: float) -> float:
    """
    Compute the theoretical asymptotic BB84 secret fraction.

    r(Q) = 1 - 2 * h₂(Q)

    Parameters
    ----------
    qber : float
        Estimated Quantum Bit Error Rate.

    Returns
    -------
    float
        Secret fraction (clipped at 0).
    """
    return max(1.0 - 2.0 * binary_entropy(qber), 0.0)


# ============================================================
# QUANTUM PRIMITIVES
# ============================================================

def prepare_qubit(bit: int, basis: int) -> QuantumCircuit:
    """
    Prepare a single BB84 qubit.

    Encoding:
        basis = 0 (Z / computational basis):
            bit 0 → |0⟩
            bit 1 → |1⟩
        basis = 1 (X / Hadamard basis):
            bit 0 → |+⟩ = (|0⟩ + |1⟩)/√2
            bit 1 → |−⟩ = (|0⟩ - |1⟩)/√2

    Parameters
    ----------
    bit : int
        Classical bit to encode (0 or 1).
    basis : int
        Encoding basis (0 = Z, 1 = X).

    Returns
    -------
    QuantumCircuit
        Circuit containing the prepared qubit.
    """
    qc = QuantumCircuit(1, 1)
    bit, basis = int(bit), int(basis)

    if basis == 0:          # Z basis
        if bit == 1:
            qc.x(0)
    else:                   # X basis
        if bit == 1:
            qc.x(0)
        qc.h(0)

    return qc


def measure_qubit(qc: QuantumCircuit, basis: int) -> int:
    """
    Measure a qubit in the specified BB84 basis.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit containing the qubit to measure.
    basis : int
        Measurement basis (0 = Z, 1 = X).

    Returns
    -------
    int
        Measurement outcome (0 or 1).
    """
    meas_qc = qc.copy()
    if int(basis) == 1:
        meas_qc.h(0)        # Rotate X-basis measurement to Z-basis
    meas_qc.measure(0, 0)

    result = simulator.run(meas_qc, shots=1).result()
    counts = result.get_counts()
    return int(next(iter(counts)))


# ============================================================
# CHANNEL MODELS
# ============================================================

def apply_channel_noise(qc: QuantumCircuit,
                        p_loss: float = 0.0,
                        p_depolarizing: float = 0.0):
    """
    Apply a simplified quantum channel model.

    - Photon loss: the qubit is discarded with probability p_loss.
    - Depolarizing noise: currently implemented as a bit-flip (X) channel
      with probability p_depolarizing.

    Parameters
    ----------
    qc : QuantumCircuit
        Input quantum circuit.
    p_loss : float
        Probability that the photon is lost.
    p_depolarizing : float
        Probability of a bit-flip error.

    Returns
    -------
    tuple
        (qc_after_noise, was_lost)
        was_lost is True if the photon was lost.
    """
    if not (0.0 <= p_loss <= 1.0 and 0.0 <= p_depolarizing <= 1.0):
        raise ValueError("Probabilities must be in the interval [0, 1]")

    rng = secrets.SystemRandom()

    # Photon loss
    if rng.random() < p_loss:
        return None, True

    qc_noisy = qc.copy()

    # Simplified bit-flip noise
    if rng.random() < p_depolarizing:
        qc_noisy.x(0)

    return qc_noisy, False


def apply_dark_counts(measured_bit: int, p_dark: float = 0.0) -> int:
    """
    Apply a simple dark-count model by randomly flipping the measured bit.

    Parameters
    ----------
    measured_bit : int
        Original measurement result.
    p_dark : float
        Probability of a dark-count induced flip.

    Returns
    -------
    int
        Possibly flipped measurement result.
    """
    if secrets.SystemRandom().random() < p_dark:
        return 1 - int(measured_bit)
    return int(measured_bit)


# ============================================================
# BB84 KEY EXCHANGE
# ============================================================

def run_bb84_exchange(n_qubits: int,
                      p_eve: float = 0.0,
                      p_loss: float = 0.0,
                      p_depolarizing: float = 0.0,
                      p_dark_counts: float = 0.0) -> dict:
    """
    Execute the quantum transmission phase of BB84.

    Alice prepares and sends qubits. The channel may be affected by
    photon loss, noise, and an intercept-resend attack by Eve.
    Bob measures the received qubits.

    Parameters
    ----------
    n_qubits : int
        Number of qubits to transmit.
    p_eve : float
        Probability that Eve intercepts a given qubit.
    p_loss : float
        Photon loss probability.
    p_depolarizing : float
        Probability of a bit-flip error.
    p_dark_counts : float
        Dark-count probability.

    Returns
    -------
    dict
        Dictionary containing Alice's bits/bases, Bob's results,
        loss information and Eve's interception record.
    """
    if n_qubits <= 0:
        raise ValueError("n_qubits must be positive")

    alice_bits = secure_random_bits(n_qubits)
    alice_basis = secure_random_bits(n_qubits)
    bob_basis = secure_random_bits(n_qubits)

    bob_results = np.full(n_qubits, -1, dtype=int)
    photon_lost = np.zeros(n_qubits, dtype=bool)
    eve_intercepted = np.zeros(n_qubits, dtype=bool)

    rng = secrets.SystemRandom()

    for i in range(n_qubits):
        # Alice prepares the qubit
        qc = prepare_qubit(int(alice_bits[i]), int(alice_basis[i]))

        # Channel transmission
        qc, was_lost = apply_channel_noise(qc, p_loss, p_depolarizing)
        if was_lost:
            photon_lost[i] = True
            continue

        # Eve's intercept-resend attack
        if rng.random() < p_eve:
            e_basis = secrets.randbits(1)
            e_bit = measure_qubit(qc, e_basis)
            qc = prepare_qubit(e_bit, e_basis)   # Eve resends a new qubit
            eve_intercepted[i] = True

        # Bob measures
        bob_bit = measure_qubit(qc, int(bob_basis[i]))
        bob_bit = apply_dark_counts(bob_bit, p_dark_counts)
        bob_results[i] = bob_bit

    return {
        "alice_bits": alice_bits,
        "alice_basis": alice_basis,
        "bob_basis": bob_basis,
        "bob_results": bob_results,
        "photon_lost": photon_lost,
        "eve_intercepted": eve_intercepted,
    }


# ============================================================
# SIFTING
# ============================================================

def sift_keys(alice_bits, alice_basis, bob_basis, bob_results, photon_lost):
    """
    Perform basis sifting.

    Only positions where:
    - Alice and Bob used the same basis, and
    - the photon was not lost
    are retained.

    Returns
    -------
    positions, alice_sifted, bob_sifted, sifting_efficiency
    """
    valid = (alice_basis == bob_basis) & (~photon_lost) & (bob_results != -1)
    positions = np.where(valid)[0]

    alice_sifted = alice_bits[positions]
    bob_sifted = bob_results[positions]
    efficiency = len(positions) / len(alice_bits) if len(alice_bits) > 0 else 0.0

    return positions, alice_sifted, bob_sifted, efficiency


# ============================================================
# PARAMETER ESTIMATION & ABORT
# ============================================================

def parameter_estimation(alice_sifted, bob_sifted,
                         estimation_fraction: float = ESTIMATION_FRACTION):
    """
    Perform parameter estimation by sacrificing a random sample.

    A fraction of the sifted bits is publicly compared to estimate the QBER.
    These bits are removed from the key material.

    Returns
    -------
    qber, alice_key_bits, bob_key_bits, n_estimation_bits
    """
    n = len(alice_sifted)
    if n == 0:
        return 0.0, np.array([], dtype=int), np.array([], dtype=int), 0

    n_est = max(1, int(n * estimation_fraction))
    indices = np.arange(n)
    np.random.shuffle(indices)

    est_idx = indices[:n_est]
    key_idx = indices[n_est:]

    qber = np.sum(alice_sifted[est_idx] != bob_sifted[est_idx]) / n_est
    return qber, alice_sifted[key_idx], bob_sifted[key_idx], n_est


def check_abort_condition(qber: float, threshold: float = Q_THRESHOLD) -> bool:
    """
    Decide whether the protocol should abort.

    Returns True if the estimated QBER exceeds the security threshold.
    """
    return qber > threshold


# ============================================================
# ERROR RECONCILIATION
# ============================================================

def block_parity(bits) -> int:
    """Compute the XOR parity of a block of bits."""
    if len(bits) == 0:
        return 0
    return int(np.bitwise_xor.reduce(bits))


def binary_search_correct(alice_block, bob_block, leaked):
    """
    Locate and correct a single error using interactive parity checks.
    Correctly handles the edge case of a block of size 1.
    """
    n = len(alice_block)

    if n == 1:
        corrected = bob_block.copy()
        if corrected[0] != alice_block[0]:
            corrected[0] = alice_block[0]
        return corrected

    mid = n // 2
    leaked[0] += 1          # one parity bit is revealed

    if block_parity(alice_block[:mid]) != block_parity(bob_block[:mid]):
        left = binary_search_correct(alice_block[:mid], bob_block[:mid], leaked)
        return np.concatenate([left, bob_block[mid:]])
    else:
        right = binary_search_correct(alice_block[mid:], bob_block[mid:], leaked)
        return np.concatenate([bob_block[:mid], right])


def reconcile_keys(alice_key, bob_key, block_size: int = 8):
    """
    Perform simplified parity-based error reconciliation.

    Returns
    -------
    reconciled_bob_key : np.ndarray
    leak_EC : int
        Number of parity bits revealed during reconciliation.
    """
    bob_rec = bob_key.copy()
    leaked = [0]

    for start in range(0, len(alice_key), block_size):
        end = min(start + block_size, len(alice_key))
        a_block = alice_key[start:end]
        b_block = bob_rec[start:end]

        leaked[0] += 1
        if block_parity(a_block) != block_parity(b_block):
            bob_rec[start:end] = binary_search_correct(a_block, b_block, leaked)

    return bob_rec, leaked[0]


# ============================================================
# PRIVACY AMPLIFICATION
# ============================================================

def generate_toeplitz_matrix(m: int, n: int):
    """
    Generate a random binary m × n Toeplitz matrix for universal hashing.
    """
    if m <= 0 or n <= 0:
        return np.empty((max(m, 0), max(n, 0)), dtype=int)

    first_col = np.array([secrets.randbits(1) for _ in range(m)], dtype=int)
    first_row = np.array([secrets.randbits(1) for _ in range(n)], dtype=int)
    first_row[0] = first_col[0]

    return toeplitz(first_col, first_row)


def apply_toeplitz(T, key_bits):
    """Apply the Toeplitz matrix to the key (binary matrix-vector product mod 2)."""
    if T.size == 0:
        return np.array([], dtype=int)
    return (T @ key_bits) % 2


def choose_final_key_length(n_key: int, leaked_bits: int, qber: float,
                            margin: int = 40) -> int:
    """
    Estimate the length of the final secret key.

    The estimate follows the spirit of the asymptotic formula:
        final ≈ n_key * (1 - 2 h₂(Q)) - leak_EC - security_margin
    """
    if n_key <= 0:
        return 0
    r = asymptotic_secret_fraction(qber)
    return max(int(r * n_key) - leaked_bits - margin, 0)


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def run_full_pipeline(n_qubits: int,
                      p_eve: float = 0.0,
                      p_loss: float = 0.0,
                      p_depolarizing: float = 0.0,
                      p_dark_counts: float = 0.0,
                      verbose: bool = True) -> dict:
    """
    Execute the complete BB84 pipeline:

    1. Quantum transmission
    2. Sifting
    3. Parameter estimation
    4. Abort decision
    5. Error reconciliation
    6. Privacy amplification

    Returns a dictionary containing all relevant metrics.
    """
    raw = run_bb84_exchange(n_qubits, p_eve, p_loss, p_depolarizing, p_dark_counts)

    _, alice_sifted, bob_sifted, sift_eff = sift_keys(
        raw["alice_bits"], raw["alice_basis"],
        raw["bob_basis"], raw["bob_results"],
        raw["photon_lost"]
    )

    qber, alice_key, bob_key, n_est = parameter_estimation(alice_sifted, bob_sifted)
    abort = check_abort_condition(qber)

    result = {
        "sift_eff": sift_eff,
        "qber": qber,
        "abort": abort,
        "n_est": n_est,
        "n_key": len(alice_key),
        "final_len": 0,
        "leak_EC": 0,
        "keys_match": False,
        "theory_r": asymptotic_secret_fraction(qber)
    }

    if abort:
        if verbose:
            print(f"  ✗ ABORT  | QBER = {qber:.4f}")
        return result

    # Error reconciliation
    bob_rec, leak_EC = reconcile_keys(alice_key, bob_key)
    result["leak_EC"] = leak_EC

    # Privacy amplification
    final_len = choose_final_key_length(len(alice_key), leak_EC, qber)
    result["final_len"] = final_len

    if final_len > 0:
        T = generate_toeplitz_matrix(final_len, len(alice_key))
        alice_final = apply_toeplitz(T, alice_key)
        bob_final = apply_toeplitz(T, bob_rec)
        result["keys_match"] = np.array_equal(alice_final, bob_final)

    if verbose:
        print(f"  ✓ CONTINUE | QBER={qber:.4f} | "
              f"key_bits={len(alice_key)} | final={final_len} | "
              f"match={result['keys_match']}")

    return result


# ============================================================
# OPTIONAL EXPERIMENTS
# ============================================================

def experiment_eve_noise_heatmap(n_qubits: int = 1200):
    """
    Generate a 2-D heatmap of QBER as a function of
    Eve's attack probability and channel noise strength.
    """
    print("\n[Optional Experiment] Eve × Noise Heatmap")
    print("-" * 80)

    p_eve_values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    noise_values = [0.0, 0.01, 0.02, 0.05, 0.10]

    heatmap = np.zeros((len(noise_values), len(p_eve_values)))

    for i, noise in enumerate(noise_values):
        for j, p_eve in enumerate(p_eve_values):
            res = run_full_pipeline(n_qubits, p_eve=p_eve,
                                    p_depolarizing=noise, verbose=False)
            heatmap[i, j] = res["qber"]
            print(f"  noise={noise:.2f}, p_eve={p_eve:.1f} → QBER={res['qber']:.4f}")

    plt.figure(figsize=(9, 6))
    im = plt.imshow(heatmap, origin="lower", aspect="auto", cmap="viridis")
    plt.colorbar(im, label="QBER")
    plt.xticks(range(len(p_eve_values)), [f"{p:.1f}" for p in p_eve_values])
    plt.yticks(range(len(noise_values)), [f"{n:.2f}" for n in noise_values])
    plt.xlabel("Eve attack probability $p_{Eve}$")
    plt.ylabel("Depolarizing noise probability")
    plt.title("QBER Heatmap: Eve Attack Strength × Channel Noise")
    plt.tight_layout()
    plt.savefig("eve_noise_heatmap.png", dpi=150)
    print("✓ Saved: eve_noise_heatmap.png")


def experiment_finite_key_sweep():
    """
    Study finite-key effects by measuring QBER variance
    and abort rate for different key sizes.
    """
    print("\n[Optional Experiment] Finite-Key Sweep")
    print("-" * 80)

    key_sizes = [200, 500, 1000, 2000, 4000]
    n_trials = 6

    mean_qbers, std_qbers, abort_rates = [], [], []

    for n in key_sizes:
        qbers = []
        aborts = 0
        for _ in range(n_trials):
            res = run_full_pipeline(n, p_eve=0.25, verbose=False)
            qbers.append(res["qber"])
            if res["abort"]:
                aborts += 1

        mean_qbers.append(np.mean(qbers))
        std_qbers.append(np.std(qbers))
        abort_rates.append(aborts / n_trials)

        print(f"  n={n:4d} | mean QBER={mean_qbers[-1]:.4f} ± {std_qbers[-1]:.4f} "
              f"| abort rate={abort_rates[-1]:.2f}")

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.errorbar(key_sizes, mean_qbers, yerr=std_qbers, fmt="o-",
                 capsize=4, label="Mean QBER ± std")
    ax1.axhline(Q_THRESHOLD, color="red", linestyle=":", label="Abort threshold")
    ax1.set_xlabel("Number of qubits sent")
    ax1.set_ylabel("QBER")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(key_sizes, abort_rates, "s--", color="orange", label="Abort rate")
    ax2.set_ylabel("Abort rate")
    ax2.legend(loc="upper right")

    plt.title("Finite-Key Effects: QBER Variance & Abort Rate vs Key Size")
    plt.tight_layout()
    plt.savefig("finite_key_sweep.png", dpi=150)
    print("✓ Saved: finite_key_sweep.png")


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("BB84 Quantum Key Distribution Simulation")
    print("Team QRYPTQ | Alexandria Quantum Hackathon 2026")
    print("=" * 80)

    n_qubits = 2000

    # ----------------------------------------------------------
    # Core validation tests
    # ----------------------------------------------------------
    print("\n[TEST 1] Ideal baseline (No Eve, No Noise)")
    print("-" * 80)
    run_full_pipeline(n_qubits, p_eve=0.0)

    print("\n[TEST 2] Noise only (False-positive check)")
    print("-" * 80)
    run_full_pipeline(n_qubits, p_eve=0.0, p_loss=0.04,
                      p_depolarizing=0.015, p_dark_counts=0.008)

    print("\n[TEST 3] Noise + Eve")
    print("-" * 80)
    run_full_pipeline(n_qubits, p_eve=0.35, p_loss=0.04,
                      p_depolarizing=0.015, p_dark_counts=0.008)

    # ----------------------------------------------------------
    # Main required plots
    # ----------------------------------------------------------
    print("\n[TEST 4] QBER vs Eve Attack Strength")
    print("-" * 80)

    p_values = np.linspace(0.0, 1.0, 11)
    qbers = []

    for p in p_values:
        res = run_full_pipeline(3000, p_eve=p, verbose=False)
        qbers.append(res["qber"])
        status = "ABORT" if res["abort"] else "OK"
        print(f"  p_eve={p:.2f} → QBER={res['qber']:.4f}  (theory ≈ {p/4:.4f})  [{status}]")

    plt.figure(figsize=(8, 5))
    plt.plot(p_values, qbers, "o-", linewidth=2, label="Simulated QBER")
    plt.plot(p_values, np.array(p_values) / 4, "--", linewidth=2, label="Theory QBER = p/4")
    plt.axhline(Q_THRESHOLD, color="red", linestyle=":", label=f"Abort threshold ({Q_THRESHOLD})")
    plt.xlabel("Eve attack probability $p_{Eve}$")
    plt.ylabel("QBER")
    plt.title("QBER vs Intercept-Resend Attack Strength")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("qber_vs_attack_strength.png", dpi=150)
    print("✓ Saved: qber_vs_attack_strength.png")

    print("\n[TEST 5] Final Key Rate vs QBER")
    print("-" * 80)

    p_values_kr = np.linspace(0.0, 0.55, 10)
    qbers_kr, rates, theory_rates = [], [], []

    for p in p_values_kr:
        res = run_full_pipeline(2500, p_eve=p, verbose=False)
        q = res["qber"]
        rate = res["final_len"] / 2500
        th = res["theory_r"] * res["sift_eff"] * (1 - ESTIMATION_FRACTION)

        qbers_kr.append(q)
        rates.append(rate)
        theory_rates.append(max(th, 0.0))
        print(f"  QBER={q:.4f} → rate={rate:.4f}  (theory ≈ {th:.4f})")

    plt.figure(figsize=(8, 5))
    plt.plot(qbers_kr, rates, "o-", linewidth=2, label="Simulated final key rate")
    plt.plot(qbers_kr, theory_rates, "--", linewidth=2, label="Theoretical asymptotic rate")
    plt.axvline(Q_THRESHOLD, color="red", linestyle=":", label=f"Abort threshold ({Q_THRESHOLD})")
    plt.xlabel("QBER")
    plt.ylabel("Secret key rate (bits / qubit sent)")
    plt.title("Final Secret Key Rate vs QBER")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("keyrate_vs_qber.png", dpi=150)
    print("✓ Saved: keyrate_vs_qber.png")

    # ----------------------------------------------------------
    # Optional experiments
    # ----------------------------------------------------------
    experiment_eve_noise_heatmap(n_qubits=1200)
    experiment_finite_key_sweep()

    print("\n" + "=" * 80)
    print("ALL EXPERIMENTS COMPLETED SUCCESSFULLY")
    print("Generated figures:")
    print("  1. qber_vs_attack_strength.png")
    print("  2. keyrate_vs_qber.png")
    print("  3. eve_noise_heatmap.png")
    print("  4. finite_key_sweep.png")
    print("=" * 80)
