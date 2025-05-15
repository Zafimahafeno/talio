<?php
require_once('../db.php');

header('Content-Type: application/json');

$price = $_POST['price'] ?? null;
$user_id = $_POST['user_id'] ?? 1;

if (!$price) {
    http_response_code(400);
    echo json_encode(["error" => "Prix non fourni."]);
    exit;
}

// Logique simple : à personnaliser plus tard
$trend = ($price > 100) ? "buy" : (($price < 90) ? "sell" : "wait");

echo json_encode(["signal" => $trend]);
?>
