<?php
// fetch_trades.php

require_once('db.php');

$user_id = 1;

$stmt = $pdo->prepare("SELECT * FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT 5");
$stmt->execute([$user_id]);
$trades = $stmt->fetchAll(PDO::FETCH_ASSOC);

foreach ($trades as $trade) {
    echo "<tr>";
    echo "<td>" . htmlspecialchars($trade['created_at']) . "</td>";
    echo "<td>" . strtoupper(htmlspecialchars($trade['signal'])) . "</td>";
    echo "<td>$" . number_format((float)$trade['price'], 2) . "</td>";
    echo "<td>$" . number_format((float)$trade['amount'], 2) . "</td>";
    echo "</tr>";
}
?>
