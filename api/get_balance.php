<?php
header('Content-Type: application/json');

// Appel vers le serveur Python Flask (localhost sur port 5001)
$response = @file_get_contents('http://127.0.0.1:5001/balance');

if ($response === false) {
    echo json_encode(["error" => "Impossible de contacter le serveur MT5 Flask"]);
} else {
    echo $response;
}
?>
