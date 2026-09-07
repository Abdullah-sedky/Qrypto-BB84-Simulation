import numpy as np
import secrets
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from scipy.linalg import toeplitz


# ============================================================
# SETUP
# ============================================================

simulator = AerSimulator()

# Abort if QBER exceeds 11%
Q_THRESHOLD = 0.11


# ============================================================
# SECURE RANDOMNESS
# ============================================================

def secure_random_bits(n):
    return np.array(
        [secrets.randbits(1) for _ in range(n)],
        dtype=int
    )


# ============================================================
# QUBIT PREPARATION
# ============================================================

def prepare_qubit(bit, basis):
    """
    Prepare one BB84 qubit.

    basis = 0 -> Z basis
        bit 0 -> |0>
        bit 1 -> |1>

    basis = 1 -> X basis
        bit 0 -> |+>
        bit 1 -> |->
    """

    qc = QuantumCircuit(1, 1)

    bit = int(bit)
    basis = int(basis)

    if basis == 0:
        # Z basis
        if bit == 1:
            qc.x(0)

    else:
        # X basis
        if bit == 1:
            qc.x(0)
        qc.h(0)

    return qc


# ============================================================
# QUBIT MEASUREMENT
# ============================================================

def measure_qubit(qc, basis):
    """
    Measure a qubit in the requested BB84 basis.

    basis = 0 -> Z basis
    basis = 1 -> X basis
    """

    meas_qc = qc.copy()

    basis = int(basis)

    if basis == 1:
        # Rotate X basis to Z basis before measurement
        meas_qc.h(0)

    meas_qc.measure(0, 0)

    result = simulator.run(
        meas_qc,
        shots=1
    ).result()

    counts = result.get_counts()

    bit = int(next(iter(counts)))

    return bit


# ============================================================
# CHANNEL NOISE
# ============================================================

def apply_channel_noise(qc, p_loss=0.0, p_depolarizing=0.0):
    """
    Apply the current simplified channel-noise model.

    p_loss:
        Probability that the photon is lost.

    p_depolarizing:
        Current simplified model: probability of an X/bit-flip
        error occurring on the qubit.

    Returns:
        (qc_after_noise, was_lost)
    """

    rng = secrets.SystemRandom()

    # Photon loss
    if rng.random() < p_loss:
        return None, True

    qc_noisy = qc.copy()

    # Simplified bit-flip noise model
    if rng.random() < p_depolarizing:
        qc_noisy.x(0)

    return qc_noisy, False


# ============================================================
# DARK COUNTS
# ============================================================

def apply_dark_counts(measured_bit, p_dark_counts=0.0):
    """
    Simplified dark-count model:
    randomly flips the measured bit with probability p_dark_counts.
    """

    if secrets.SystemRandom().random() < p_dark_counts:
        return 1 - int(measured_bit)

    return int(measured_bit)


# ============================================================
# BB84 KEY EXCHANGE
# ============================================================

def run_bb84_exchange(
    n_qubits,
    p_eve=0.0,
    p_loss=0.0,
    p_depolarizing=0.0,
    p_dark_counts=0.0
):
    """
    Run BB84 key exchange with Eve and channel-noise support.
    """

    alice_bits = secure_random_bits(n_qubits)
    alice_basis = secure_random_bits(n_qubits)
    bob_basis = secure_random_bits(n_qubits)

    # -1 means no valid Bob measurement
    bob_results = np.full(
        n_qubits,
        -1,
        dtype=int
    )

    photon_lost = np.zeros(
        n_qubits,
        dtype=bool
    )

    eve_intercepted = np.zeros(
        n_qubits,
        dtype=bool
    )

    eve_basis_arr = np.full(
        n_qubits,
        -1,
        dtype=int
    )

    eve_bits_arr = np.full(
        n_qubits,
        -1,
        dtype=int
    )

    rng = secrets.SystemRandom()

    for i in range(n_qubits):

        bit = int(alice_bits[i])
        basis = int(alice_basis[i])

        # ----------------------------------------------------
        # Alice prepares the qubit
        # ----------------------------------------------------

        qc = prepare_qubit(
            bit,
            basis
        )

        # ----------------------------------------------------
        # Channel noise / loss
        # ----------------------------------------------------

        qc, was_lost = apply_channel_noise(
            qc,
            p_loss=p_loss,
            p_depolarizing=p_depolarizing
        )

        if was_lost:
            photon_lost[i] = True
            bob_results[i] = -1
            continue

        # ----------------------------------------------------
        # Eve intercept-resend
        # ----------------------------------------------------

        intercepts = rng.random() < p_eve

        if intercepts:

            e_basis = secrets.randbits(1)

            e_bit = measure_qubit(
                qc,
                e_basis
            )

            # Eve prepares a fresh qubit
            qc = prepare_qubit(
                e_bit,
                e_basis
            )

            eve_intercepted[i] = True
            eve_basis_arr[i] = e_basis
            eve_bits_arr[i] = e_bit

        # ----------------------------------------------------
        # Bob measurement
        # ----------------------------------------------------

        b_basis = int(bob_basis[i])

        bob_bit = measure_qubit(
            qc,
            b_basis
        )

        # ----------------------------------------------------
        # Dark count model
        # ----------------------------------------------------

        bob_bit = apply_dark_counts(
            bob_bit,
            p_dark_counts=p_dark_counts
        )

        bob_results[i] = bob_bit

    return {
        "alice_bits": alice_bits,
        "alice_basis": alice_basis,
        "bob_basis": bob_basis,
        "bob_results": bob_results,
        "eve_intercepted": eve_intercepted,
        "eve_basis": eve_basis_arr,
        "eve_bits": eve_bits_arr,
        "photon_lost": photon_lost,
    }


# ============================================================
# SIFTING
# ============================================================

def sift_keys(
    alice_bits,
    alice_basis,
    bob_basis,
    bob_results,
    photon_lost
):
    """
    Keep only positions where:

    1. Alice and Bob used the same basis
    2. Photon was not lost
    3. Bob has a valid measurement
    """

    n = len(alice_bits)

    valid = (
        (alice_basis == bob_basis)
        & (~photon_lost)
        & (bob_results != -1)
    )

    matching_positions = np.where(valid)[0]

    alice_sifted = alice_bits[
        matching_positions
    ]

    bob_sifted = bob_results[
        matching_positions
    ]

    sifting_efficiency = (
        len(matching_positions) / n
        if n > 0
        else 0.0
    )

    return (
        matching_positions,
        alice_sifted,
        bob_sifted,
        sifting_efficiency
    )


# ============================================================
# QBER
# ============================================================

def compute_qber(
    alice_sifted,
    bob_sifted
):
    """
    QBER = number of mismatched bits /
           total sifted bits
    """

    n_sifted = len(alice_sifted)

    if n_sifted == 0:
        return 0.0

    n_errors = np.sum(
        alice_sifted != bob_sifted
    )

    return n_errors / n_sifted


# ============================================================
# ABORT CONDITION
# ============================================================

def check_abort_condition(
    qber,
    q_threshold=Q_THRESHOLD
):
    """
    Returns True if the measured QBER exceeds
    the configured abort threshold.
    """

    return qber > q_threshold


# ============================================================
# QBER VS EVE ATTACK STRENGTH
# ============================================================

def sweep_qber_vs_attack_strength(
    n_qubits,
    p_values
):
    """
    Run BB84 for different Eve attack probabilities.
    """

    qbers = np.zeros(
        len(p_values)
    )

    for idx, p in enumerate(p_values):

        result = run_bb84_exchange(
            n_qubits,
            p_eve=float(p)
        )

        (
            _,
            alice_sifted,
            bob_sifted,
            _
        ) = sift_keys(
            result["alice_bits"],
            result["alice_basis"],
            result["bob_basis"],
            result["bob_results"],
            result["photon_lost"]
        )

        qbers[idx] = compute_qber(
            alice_sifted,
            bob_sifted
        )

    return qbers


# ============================================================
# PARITY
# ============================================================

def block_parity(bits):
    """
    Calculate XOR parity of a block.
    """

    if len(bits) == 0:
        return 0

    return int(
        np.bitwise_xor.reduce(bits)
    )


# ============================================================
# BINARY SEARCH FOR ERROR
# ============================================================

def binary_search_correct(
    alice_block,
    bob_block,
    leaked_bits_counter
):
    """
    Locate one mismatched bit using parity checks
    and correct Bob's copy.

    leaked_bits_counter[0] tracks disclosed parity
    information.
    """

    n = len(alice_block)

    # A single-bit block with different parity
    # means this bit is incorrect.
    if n == 1:

        corrected_block = bob_block.copy()

        if corrected_block[0] != alice_block[0]:
            corrected_block[0] = alice_block[0]

        return corrected_block

    mid = n // 2

    a_left = alice_block[:mid]
    a_right = alice_block[mid:]

    b_left = bob_block[:mid]
    b_right = bob_block[mid:]

    # One parity bit is revealed
    leaked_bits_counter[0] += 1

    if block_parity(a_left) != block_parity(b_left):

        corrected_left = binary_search_correct(
            a_left,
            b_left,
            leaked_bits_counter
        )

        return np.concatenate(
            [corrected_left, b_right]
        )

    else:

        corrected_right = binary_search_correct(
            a_right,
            b_right,
            leaked_bits_counter
        )

        return np.concatenate(
            [b_left, corrected_right]
        )


# ============================================================
# ERROR RECONCILIATION
# ============================================================

def reconcile_keys(
    alice_sifted,
    bob_sifted,
    block_size=8
):
    """
    Simplified parity-based error reconciliation.

    Returns:
        reconciled Bob key
        number of leaked parity bits
    """

    n = len(alice_sifted)

    bob_reconciled = bob_sifted.copy()

    leaked_bits = [0]

    for start in range(
        0,
        n,
        block_size
    ):

        end = min(
            start + block_size,
            n
        )

        a_block = alice_sifted[
            start:end
        ]

        b_block = bob_reconciled[
            start:end
        ]

        # Reveal one parity bit
        leaked_bits[0] += 1

        if block_parity(a_block) != block_parity(b_block):

            corrected_block = binary_search_correct(
                a_block,
                b_block,
                leaked_bits
            )

            bob_reconciled[
                start:end
            ] = corrected_block

    return (
        bob_reconciled,
        leaked_bits[0]
    )


# ============================================================
# TOEPLITZ PRIVACY AMPLIFICATION
# ============================================================

def generate_toeplitz_matrix(m, n):
    """
    Generate an m x n Toeplitz binary matrix.
    """

    if m <= 0 or n <= 0:
        return np.empty(
            (max(m, 0), max(n, 0)),
            dtype=int
        )

    first_col = np.array(
        [secrets.randbits(1) for _ in range(m)],
        dtype=int
    )

    first_row = np.array(
        [secrets.randbits(1) for _ in range(n)],
        dtype=int
    )

    first_row[0] = first_col[0]

    return toeplitz(
        first_col,
        first_row
    )


def apply_toeplitz(
    T,
    key_bits
):
    """
    Apply binary Toeplitz hashing.
    """

    if T.size == 0:
        return np.array([], dtype=int)

    return (
        T @ key_bits
    ) % 2


# ============================================================
# BINARY ENTROPY
# ============================================================

def binary_entropy(q):
    """
    Binary Shannon entropy h2(q).
    """

    if q <= 0.0 or q >= 1.0:
        return 0.0

    return (
        -q * np.log2(q)
        - (1 - q) * np.log2(1 - q)
    )


# ============================================================
# FINAL KEY LENGTH
# ============================================================

def choose_final_key_length(
    sifted_length,
    leaked_bits,
    qber,
    security_margin=50
):
    """
    Current simplified key-length estimation.

    This keeps the same model as the original code.
    """

    if sifted_length <= 0:
        return 0

    h = binary_entropy(qber)

    eve_info_estimate = int(
        h * sifted_length
    )

    shrink = (
        leaked_bits
        + eve_info_estimate
        + security_margin
    )

    return max(
        sifted_length - shrink,
        0
    )


# ============================================================
# MAIN TESTS
# ============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("BB84 QKD - WITH ABORT THRESHOLD & NOISE")
    print("=" * 80)

    n_qubits = 500

    # ========================================================
    # TEST 1: NO EVE, NO NOISE
    # ========================================================

    print(
        "\n[TEST 1] Baseline: No Eve, No Noise"
    )

    print("-" * 80)

    result = run_bb84_exchange(
        n_qubits,
        p_eve=0.0,
        p_loss=0.0,
        p_depolarizing=0.0,
        p_dark_counts=0.0
    )

    (
        _,
        alice_sifted,
        bob_sifted,
        sift_eff
    ) = sift_keys(
        result["alice_bits"],
        result["alice_basis"],
        result["bob_basis"],
        result["bob_results"],
        result["photon_lost"]
    )

    qber = compute_qber(
        alice_sifted,
        bob_sifted
    )

    # Abort decision
    if check_abort_condition(qber):

        print(
            f"✗ ABORT: QBER {qber:.4f} "
            f"exceeds threshold {Q_THRESHOLD:.4f}"
        )

    else:

        print(
            f"✓ CONTINUE: QBER {qber:.4f} "
            f"below threshold {Q_THRESHOLD:.4f}"
        )

    # Reconciliation
    bob_reconciled, leaked_bits = reconcile_keys(
        alice_sifted,
        bob_sifted
    )

    print(
        f"Reconciled match: "
        f"{np.array_equal(alice_sifted, bob_reconciled)}"
    )

    # Current simplified privacy amplification
    final_len = choose_final_key_length(
        len(alice_sifted),
        leaked_bits,
        qber
    )

    if final_len > 0:

        T = generate_toeplitz_matrix(
            final_len,
            len(alice_sifted)
        )

        alice_final_key = apply_toeplitz(
            T,
            alice_sifted
        )

        bob_final_key = apply_toeplitz(
            T,
            bob_reconciled
        )

    else:

        alice_final_key = np.array(
            [],
            dtype=int
        )

        bob_final_key = np.array(
            [],
            dtype=int
        )

    print(
        f"Final keys match: "
        f"{np.array_equal(alice_final_key, bob_final_key)}"
    )

    print(
        f"Final secure key length: {final_len}"
    )

    print(
        f"n_qubits sent        : {n_qubits}"
    )

    print(
        f"sifted key length    : {len(alice_sifted)}"
    )

    print(
        f"sifting efficiency   : {sift_eff:.4f} "
        f"(expected ~0.50)"
    )

    print(
        f"QBER (no Eve)        : {qber:.4f} "
        f"(expected ~0.00)"
    )

    print(
        f"Alice/Bob keys match : "
        f"{np.array_equal(alice_sifted, bob_sifted)}"
    )

    print(
        f"leak_EC              : {leaked_bits}"
    )

    # ========================================================
    # TEST 2: NOISE ONLY
    # ========================================================

    print(
        "\n[TEST 2] With Noise, No Eve "
        "(False-Positive Test)"
    )

    print("-" * 80)

    result_noise = run_bb84_exchange(
        n_qubits,
        p_eve=0.0,
        p_loss=0.05,
        p_depolarizing=0.02,
        p_dark_counts=0.01
    )

    (
        _,
        alice_sifted_n,
        bob_sifted_n,
        sift_eff_n
    ) = sift_keys(
        result_noise["alice_bits"],
        result_noise["alice_basis"],
        result_noise["bob_basis"],
        result_noise["bob_results"],
        result_noise["photon_lost"]
    )

    qber_noise = compute_qber(
        alice_sifted_n,
        bob_sifted_n
    )

    if check_abort_condition(qber_noise):

        print(
            f"✗ ABORT: QBER {qber_noise:.4f} "
            f"exceeds threshold {Q_THRESHOLD:.4f}"
        )

        print(
            "  (This is expected for noisy channels "
            "under the current test parameters)"
        )

    else:

        print(
            f"✓ CONTINUE: QBER {qber_noise:.4f} "
            f"below threshold {Q_THRESHOLD:.4f}"
        )

    print(
        f"Sifting efficiency (with loss): "
        f"{sift_eff_n:.4f}"
    )

    print(
        f"QBER (with noise):              "
        f"{qber_noise:.4f}"
    )

    print(
        f"Photons lost: "
        f"{np.sum(result_noise['photon_lost'])} / {n_qubits}"
    )

    # ========================================================
    # TEST 3: QBER VS EVE ATTACK STRENGTH
    # ========================================================

    print(
        "\n[TEST 3] QBER vs Attack Strength "
        "(No Noise)"
    )

    print("-" * 80)

    p_values = np.linspace(
        0,
        1,
        11
    )

    avg_qbers = sweep_qber_vs_attack_strength(
        n_qubits=5000,
        p_values=p_values
    )

    print(
        "\np_eve  | measured QBER | "
        "theoretical p/4 | abort?"
    )

    for p, q in zip(
        p_values,
        avg_qbers
    ):

        abort_status = (
            "YES"
            if check_abort_condition(q)
            else "NO"
        )

        print(
            f"{p:.2f}   | "
            f"{q:.4f}        | "
            f"{p / 4:.4f}          | "
            f"{abort_status}"
        )

    # Plot
    plt.figure(
        figsize=(7, 5)
    )

    plt.plot(
        p_values,
        avg_qbers,
        "o-",
        label="Measured QBER (simulated)"
    )

    plt.plot(
        p_values,
        p_values / 4,
        "--",
        label="Theoretical QBER = p/4"
    )

    plt.axhline(
        y=Q_THRESHOLD,
        linestyle=":",
        label=f"Abort threshold ({Q_THRESHOLD:.2f})"
    )

    plt.xlabel(
        "Eve's attack strength (p)"
    )

    plt.ylabel(
        "QBER"
    )

    plt.title(
        "QBER vs. Eavesdropping Attack Strength (BB84)"
    )

    plt.legend()
    plt.grid(True)

    plt.savefig(
        "qber_vs_attack_strength.png",
        dpi=150
    )

    plt.show()

    print(
        "\n✓ Plot saved to qber_vs_attack_strength.png"
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "COMPLETE"
    )

    print(
        "=" * 80
    )
