
!pip install qiskit

!pip install qiskit-aer

import qiskit
import numpy as np
from numpy import sqrt
import secrets
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

# for simulated secure randoms
def secure_random_bits(n):
    return np.array([secrets.randbits(1) for _ in range(n)])

n_qubits = 20
p = 0.5  # Eve's attack strength, ig we can set it to 0 when trying without Eve
simulator = AerSimulator()
alice_bits = secure_random_bits(n_qubits)
alice_basis = secure_random_bits(n_qubits)
bob_basis  = secure_random_bits(n_qubits)

bob_results = []

for i in range(n_qubits):
    bit = alice_bits[i]
    basis = alice_basis[i]

    # alice creates qubit
    qc = QuantumCircuit(1, 1)
    if basis == 0:
        if bit == 1:
            qc.x(0)
    else:
        if bit == 0:
            qc.h(0)
        else:
            qc.x(0)
            qc.h(0)

eve_intercepts = secrets.SystemRandom().random() < p
if eve_intercepts:
  eve_basis = secrets.randbits(1)

# Eve measures Alice's qubit in her own random basis
if eve_basis == 1:
  qc.h(0)
qc.measure(0, 0)
result = simulator.run(qc, shots=1).result()
eve_bit = int(list(result.get_counts().keys())[0])

#Rebuild and resend
qc = QuantumCircuit(1, 1)
if eve_basis == 0:
  if eve_bit == 1:
    qc.x(0)
  else:
    if eve_bit == 0:
      qc.h(0)
    else:
      qc.x(0)
      qc.h(0)

    # Bob reaches wtv qubit reaches him
    if bob_basis[i] == 1:
        qc.h(0)
    qc.measure(0, 0)
    result = simulator.run(qc, shots=1).result()
    bob_bit = int(list(result.get_counts().keys())[0])
    bob_results.append(bob_bit)

bob_results = np.array(bob_results)
