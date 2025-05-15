<?php
require_once('../db.php');

header('Content-Type: application/json');

$user_id = $_POST['user_id'] ?? 1;
$signal = $_POST['signal'] ?? 'wait';
$price = $_POST['price'] ?? null;
$amount = $_POST['amount'] ?? 1.00;

if (!$price || $signal === 'wait') {
    echo json_encode(["message" => "Pas de décision."]);
    exit;
}

// Insertion du trade
$stmt = $pdo->prepare("INSERT INTO trades (user_id, type, amount, price, status, created_at) VALUES (?, ?, ?, ?, 'open', NOW())");
$stmt->execute([$user_id, $signal, $amount, $price]);

// Mise à jour du solde de l'utilisateur
if ($signal === "buy") {
    $stmt = $pdo->prepare("UPDATE users SET balance = balance - ? WHERE id = ?");
    $stmt->execute([$amount, $user_id]);
} elseif ($signal === "sell") {
    $stmt = $pdo->prepare("UPDATE users SET balance = balance + ? WHERE id = ?");
    $stmt->execute([$amount, $user_id]);
}

echo json_encode(["message" => "Trade '$signal' exécuté à $price."]);
?>
