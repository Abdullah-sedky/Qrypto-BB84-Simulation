import numpy as np
import secrets
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

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


# Stage 2
if __name__ == "__main__":
    n_qubits = 500  

    result = run_bb84_exchange(n_qubits, p_eve=0.0)

    positions, alice_sifted, bob_sifted, sift_eff = sift_keys(
        result["alice_bits"],
        result["alice_basis"],
        result["bob_basis"],
        result["bob_results"],
    )

    qber = compute_qber(alice_sifted, bob_sifted)

    print(f"n_qubits sent        : {n_qubits}")
    print(f"sifted key length    : {len(alice_sifted)}")
    print(f"sifting efficiency   : {sift_eff:.4f}  (expected ~0.50)")
    print(f"QBER (no Eve)        : {qber:.4f}  (expected ~0.00)")
    print(f"Alice/Bob keys match : {np.array_equal(alice_sifted, bob_sifted)}")