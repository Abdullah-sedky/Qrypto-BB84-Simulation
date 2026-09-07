import numpy as np
import secrets
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from scipy.linalg import toeplitz


simulator = AerSimulator()

def secure_random_bits(n):
    return np.array([secrets.randbits(1) for _ in range(n)])


def prepare_qubit(bit, basis):
    qc = QuantumCircuit(1, 1)
    if basis == 0:      
        if bit == 1:
            qc.x(0)
    else:                  
        if bit == 1:
            qc.x(0)
        qc.h(0)
    return qc


def measure_qubit(qc, basis):
    meas_qc = qc.copy()
    if basis == 1:
        meas_qc.h(0)
    meas_qc.measure(0, 0)
    result = simulator.run(meas_qc, shots=1).result()
    bit = int(list(result.get_counts().keys())[0])
    return bit

# Noise from photon loss and depolarizing
def apply_channel_noise(qc, p_loss=0.0, p_depolarizing=0.0):
    if secrets.SystemRandom().random() < p_loss:
        return None, True
    qc = qc.copy()
    if secrets.SystemRandom().random() < p_depolarizing:
        qc.x(0)
    return qc, False

# We could add dark counts noise as well

def run_bb84_exchange(n_qubits, p_eve=0.0):
    alice_bits = secure_random_bits(n_qubits)
    alice_basis = secure_random_bits(n_qubits)
    bob_basis = secure_random_bits(n_qubits)

    bob_results = np.zeros(n_qubits, dtype=int)
    eve_intercepted = np.zeros(n_qubits, dtype=bool)
    eve_basis_arr = np.full(n_qubits, -1, dtype=int)
    eve_bits_arr = np.full(n_qubits, -1, dtype=int)

    for i in range(n_qubits):
        bit = int(alice_bits[i])
        basis = int(alice_basis[i])

        qc = prepare_qubit(bit, basis)

        intercepts = secrets.SystemRandom().random() < p_eve
        if intercepts:
            e_basis = secrets.randbits(1)
            e_bit = measure_qubit(qc, e_basis)

            qc = prepare_qubit(e_bit, e_basis)

            eve_intercepted[i] = True
            eve_basis_arr[i] = e_basis
            eve_bits_arr[i] = e_bit
   
        b_basis = int(bob_basis[i])
        bob_bit = measure_qubit(qc, b_basis)
        bob_results[i] = bob_bit

    return {
        "alice_bits": alice_bits,
        "alice_basis": alice_basis,
        "bob_basis": bob_basis,
        "bob_results": bob_results,
        "eve_intercepted": eve_intercepted,
        "eve_basis": eve_basis_arr,
        "eve_bits": eve_bits_arr,
    }


def sift_keys(alice_bits, alice_basis, bob_basis, bob_results):

    n = len(alice_bits)
    matching_positions = np.where(alice_basis == bob_basis)[0]

    alice_sifted = alice_bits[matching_positions]
    bob_sifted = bob_results[matching_positions]

    sifting_efficiency = len(matching_positions) / n if n > 0 else 0.0

    return matching_positions, alice_sifted, bob_sifted, sifting_efficiency


def compute_qber(alice_sifted, bob_sifted):
 
    n_sifted = len(alice_sifted)
    if n_sifted == 0:
        return 0.0
    n_errors = np.sum(alice_sifted != bob_sifted)
    return n_errors / n_sifted

def sweep_qber_vs_attack_strength(n_qubits, p_values):
    # We test a few values of p for n_qubits 
    qbers = np.zeros(len(p_values))
    for idx, p in enumerate(p_values):
        result = run_bb84_exchange(n_qubits, p_eve=p)
        _, alice_sifted, bob_sifted, _ = sift_keys(
            result["alice_bits"],
            result["alice_basis"],
            result["bob_basis"],
            result["bob_results"],
        )
        qbers[idx] = compute_qber(alice_sifted, bob_sifted)
    return qbers


#Parity check for Alice and Bob
def block_parity(bits):
    return int(np.bitwise_xor.reduce(bits)) if len(bits) > 0 else 0


def binary_search_correct(alice_block, bob_block, leaked_bits_counter):
    n = len(alice_block)
    if n == 1:
        return alice_block.copy()  # found the mismatched bit, flip it

    mid = n // 2
    a_left, a_right = alice_block[:mid], alice_block[mid:]
    b_left, b_right = bob_block[:mid], bob_block[mid:]

    leaked_bits_counter[0] += 1  
    if block_parity(a_left) != block_parity(b_left):
        b_left = binary_search_correct(a_left, b_left, leaked_bits_counter)
    else:
        b_right = binary_search_correct(a_right, b_right, leaked_bits_counter)

    return np.concatenate([b_left, b_right])


def reconcile_keys(alice_sifted, bob_sifted, block_size=8):
    n = len(alice_sifted)
    bob_reconciled = bob_sifted.copy()
    leaked_bits = [0]

    for start in range(0, n, block_size):
        end = min(start + block_size, n)
        a_block = alice_sifted[start:end]
        b_block = bob_reconciled[start:end]

        leaked_bits[0] += 1 
        if block_parity(a_block) != block_parity(b_block):
            bob_reconciled[start:end] = binary_search_correct(a_block, b_block, leaked_bits)

    return bob_reconciled, leaked_bits[0]


# Toeplitz for privacy amplification
def generate_toeplitz_matrix(m, n):
    first_col = np.array([secrets.randbits(1) for _ in range(m)])
    first_row = np.array([secrets.randbits(1) for _ in range(n)])
    first_row[0] = first_col[0]
    return toeplitz(first_col, first_row)


def apply_toeplitz(T, key_bits):
    return (T @ key_bits) % 2


def binary_entropy(q):
    #Shannon entropy used to find how many bits of sifted key could have been eavesdropped, given the qber
    if q <= 0 or q >= 1:
        return 0.0
    return -q * np.log2(q) - (1 - q) * np.log2(1 - q)

# Trying to find how much the new key minimized length should be
def choose_final_key_length(sifted_length, leaked_bits, qber, security_margin=50):
    h = binary_entropy(qber)
    eve_info_estimate = int(h * sifted_length) 
    shrink = leaked_bits + eve_info_estimate + security_margin
    return max(sifted_length - shrink, 0)
 
if __name__ == "__main__":
    # Stage 2: Testing bb84 without an Eve
    n_qubits = 500
    result = run_bb84_exchange(n_qubits, p_eve=0.0)
    _, alice_sifted, bob_sifted, sift_eff = sift_keys(
    result["alice_bits"], result["alice_basis"], result["bob_basis"], result["bob_results"]
    )
    qber = compute_qber(alice_sifted, bob_sifted)

    bob_reconciled, leaked_bits = reconcile_keys(alice_sifted, bob_sifted)
    print("Reconciled match:", np.array_equal(alice_sifted, bob_reconciled))

    final_len = choose_final_key_length(len(alice_sifted), leaked_bits, qber)

    T = generate_toeplitz_matrix(final_len, len(alice_sifted))
    alice_final_key = apply_toeplitz(T, alice_sifted)
    bob_final_key = apply_toeplitz(T, bob_reconciled)

    print("Final keys match:", np.array_equal(alice_final_key, bob_final_key))
    print("Final secure key length:", final_len)
    print(f"n_qubits sent        : {n_qubits}")
    print(f"sifted key length    : {len(alice_sifted)}")
    print(f"sifting efficiency   : {sift_eff:.4f}  (expected ~0.50)")
    print(f"QBER (no Eve)        : {qber:.4f}  (expected ~0.00)")
    print(f"Alice/Bob keys match : {np.array_equal(alice_sifted, bob_sifted)}")
 
    # Stage 3: Test BB84 across a range of p
    p_values = np.linspace(0, 1, 11)   
    avg_qbers = sweep_qber_vs_attack_strength(n_qubits=5000, p_values=p_values)
 
    print("\np_eve  | measured QBER | theoretical p/4")
    for p, q in zip(p_values, avg_qbers):
        print(f"{p:.2f}   | {q:.4f}        | {p/4:.4f}")
 
    plt.figure(figsize=(7, 5))
    plt.plot(p_values, avg_qbers, 'o-', label="Measured QBER (simulated)")
    plt.plot(p_values, p_values / 4, '--', label="Theoretical QBER = p/4")
    plt.xlabel("Eve's attack strength (p)")
    plt.ylabel("QBER")
    plt.title("QBER vs. Eavesdropping Attack Strength (BB84)")
    plt.legend()
    plt.grid(True)
    plt.savefig("qber_vs_attack_strength.png", dpi=150)
    print("\nPlot saved to qber_vs_attack_strength.png")