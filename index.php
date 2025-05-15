<?php
require_once('db.php');

$user_id = 1;

// Récupération de l'utilisateur
$stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);
if (!$user) die("Utilisateur introuvable.");

// Récupération des trades
$stmt = $pdo->prepare("SELECT * FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT 5");
$stmt->execute([$user_id]);
$trades = $stmt->fetchAll(PDO::FETCH_ASSOC);
?>
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Dashboard Trading Bot</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --primary: #1976d2;
      --background: #f4f6f8;
      --white: #fff;
      --success: #2e7d32;
      --danger: #c62828;
    }
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background: var(--background);
    }
    .container {
      max-width: 960px;
      margin: 40px auto;
      padding: 30px;
      background: var(--white);
      border-radius: 12px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    }
    h1, h2 {
      color: var(--primary);
    }
    .dashboard {
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      margin-bottom: 30px;
    }
    .card {
      background: #fff;
      border-radius: 10px;
      padding: 20px;
      margin: 10px;
      flex: 1 1 45%;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
      transition: all 0.3s ease;
    }
    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .value {
      font-size: 2em;
      font-weight: bold;
      margin-top: 10px;
    }
    .status {
      display: inline-block;
      padding: 6px 12px;
      border-radius: 20px;
      font-weight: bold;
      color: #fff;
    }
    .active { background-color: var(--success); }
    .inactive { background-color: var(--danger); }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
    }
    th, td {
      padding: 12px;
      text-align: center;
      border-bottom: 1px solid #ddd;
    }
    th {
      background: var(--primary);
      color: #fff;
    }
    canvas {
      margin-top: 30px;
    }
  </style>
</head>
<body>
<div class="container">
  <h1>Bienvenue, <?= htmlspecialchars($user['username']) ?></h1>
  <div class="dashboard">
    <div class="card">
      <h2>💰 Solde actuel</h2>
      <div class="value" id="balance-amount">0</div>
    </div>
    <div class="card">
      <h2>🤖 Statut du robot</h2>
      <div class="status <?= $user['robot_active'] ? 'active' : 'inactive' ?>">
        <?= $user['robot_active'] ? 'Actif ✅' : 'Inactif ❌' ?>
      </div>
    </div>
  </div>

  <h2>📈 Historique récent</h2>
  <table>
    <thead>
      <tr><th>Date</th><th>Action</th><th>Prix</th><th>Montant</th></tr>
    </thead>
    <tbody id="trade-table-body">
      <?php foreach ($trades as $trade): ?>
        <tr>
          <td><?= htmlspecialchars($trade['created_at']) ?></td>
          <td><?= htmlspecialchars($trade['action']) ?></td>
          <td>$<?= number_format($trade['price'], 2) ?></td>
          <td>$<?= number_format($trade['amount'], 2) ?></td>
        </tr>
      <?php endforeach; ?>
    </tbody>
  </table>

  <canvas id="profitChart" height="100"></canvas>
</div>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
let currentBalance = 0;

// Animate number
function animateValue(id, start, end, duration = 500) {
  const obj = document.getElementById(id);
  let startTimestamp = null;
  const step = timestamp => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    obj.innerText = "$" + (start + (end - start) * progress).toFixed(2);
    if (progress < 1) window.requestAnimationFrame(step);
  };
  window.requestAnimationFrame(step);
}

// Fetch balance
function fetchBalance() {
  $.getJSON("http://127.0.0.1:5001/get-balance", function(data) {
    if (data.balance) {
      animateValue("balance-amount", currentBalance, data.balance);
      currentBalance = data.balance;
    }
  });
}

// Fetch trades
function fetchTrades() {
  $.ajax({
    url: 'fetch_trades.php',
    method: 'GET',
    success: function(data) {
      $('#trade-table-body').html(data);
    }
  });
}

// Profit graph
const ctx = document.getElementById('profitChart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [], // timestamps
    datasets: [{
      label: 'Profit ($)',
      data: [],
      fill: false,
      borderColor: '#1976d2',
      tension: 0.1
    }]
  },
  options: {
    responsive: true,
    animation: false,
    scales: {
      x: { title: { display: true, text: 'Heure' } },
      y: { title: { display: true, text: 'Solde ($)' } }
    }
  }
});

// Met à jour le graphique
function updateChart() {
  $.getJSON('http://127.0.0.1:5001/get-balance', function(data) {
    const time = new Date().toLocaleTimeString();
    if (chart.data.labels.length > 20) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.data.labels.push(time);
    chart.data.datasets[0].data.push(data.balance);
    chart.update();
  });
}

// Mise à jour toutes les secondes
setInterval(() => {
  fetchBalance();
  fetchTrades();
  updateChart();
}, 1000);
</script>
</body>
</html>
