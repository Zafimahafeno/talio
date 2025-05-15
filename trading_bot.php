<?php
// trading_bot.php
file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Le script s'est lancé\n", FILE_APPEND);

require_once('db.php');

$user_id = 1;

// Paramètres de la stratégie globale (pour l'activation/désactivation)
$stop_loss_threshold_global = -50; // Perte maximale globale acceptable
$take_profit_threshold_global = 50; // Gain minimal global pour reprendre le trading

// Paramètres de trading par ordre
$default_stop_loss_pips = 20; // Stop loss en pips pour chaque trade
$default_take_profit_pips = 40; // Take profit en pips pour chaque trade

// Fonction pour récupérer les données de l'API Flask
function fetch_flask_data($endpoint) {
    $url = 'http://127.0.0.1:5001/' . $endpoint;
    $data = @file_get_contents($url);
    if ($data === false) {
        file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Erreur lors de la récupération des données depuis Flask ($endpoint)\n", FILE_APPEND);
        return null;
    }
    return json_decode($data, true);
}

// Fonction pour envoyer un ordre à l'API Flask
function send_trade_order($trade_signal, $stop_loss_pips, $take_profit_pips) {
    $trade_params = [
        'type' => $trade_signal,
        'stop_loss' => $stop_loss_pips,
        'take_profit' => $take_profit_pips,
    ];
    $query_string = http_build_query($trade_params);
    $trade_url = 'http://127.0.0.1:5001/trade?' . $query_string;
    $response = @file_get_contents($trade_url);

    if ($response === false) {
        file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Erreur lors de l'envoi de l'ordre $trade_signal\n", FILE_APPEND);
        return false;
    } else {
        file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Ordre envoyé : $trade_signal - Paramètres : " . json_encode($trade_params) . " - Réponse : $response\n", FILE_APPEND);
        return true;
    }
}

// Récupérer le solde actuel depuis l'API Flask
$balance_data = fetch_flask_data('get-balance');
$current_balance = $balance_data['balance'] ?? 0;
file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Solde actuel depuis Flask : $current_balance\n", FILE_APPEND);

// Récupérer les informations de l'utilisateur et l'état du robot depuis la base de données
$stmt = $pdo->prepare("SELECT balance, robot_active FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);
$previous_balance = $user['balance'] ?? 0;
$robot_active = $user['robot_active'] ?? 0;

// Calcul de variation globale
$balance_diff_global = $current_balance - $previous_balance;
file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Solde précédent : $previous_balance, Solde actuel : $current_balance, Variation globale : $balance_diff_global\n", FILE_APPEND);

// Mise à jour du solde dans la base de données
$stmt = $pdo->prepare("UPDATE users SET balance = ? WHERE id = ?");
$update_result = $stmt->execute([$current_balance, $user_id]);
if ($update_result) {
    file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Mise à jour du solde réussi\n", FILE_APPEND);
} else {
    file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Erreur lors de la mise à jour du solde\n", FILE_APPEND);
}

// Gestion de l'activation/désactivation globale du robot
if ($balance_diff_global <= $stop_loss_threshold_global) {
    $stmt = $pdo->prepare("UPDATE users SET robot_active = 0 WHERE id = ?");
    $stmt->execute([$user_id]);
    echo "Robot stoppé globalement en raison d'une perte de $balance_diff_global dollars.\n";
    file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Robot stoppé globalement (perte globale $balance_diff_global)\n", FILE_APPEND);
    $robot_active = 0; // Mettre à jour la variable locale
} elseif ($balance_diff_global >= $take_profit_threshold_global) {
    $stmt = $pdo->prepare("UPDATE users SET robot_active = 1 WHERE id = ?");
    $stmt->execute([$user_id]);
    echo "Robot redémarré globalement après un gain de $balance_diff_global dollars.\n";
    file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Robot redémarré globalement (gain global $balance_diff_global)\n", FILE_APPEND);
    $robot_active = 1; // Mettre à jour la variable locale
} else {
    echo "Aucune action globale requise. Variation globale du solde : $balance_diff_global dollars.\n";
}

// Si le script démarre et que le robot est actif (au lancement), placer un ordre initial
if ($robot_active == 1) {
    // Simuler une analyse pour obtenir un signal initial (à remplacer par ta logique réelle)
    $initial_signal = (rand(0, 1) == 0) ? 'buy' : 'sell';
    echo "Tentative de placement d'un ordre initial au démarrage du script : $initial_signal\n";
    file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Tentative d'ordre initial : $initial_signal\n", FILE_APPEND);
    send_trade_order($initial_signal, $default_stop_loss_pips, $default_take_profit_pips);
} else {
    echo "Le robot est inactif au démarrage du script.\n";
    file_put_contents("bot_log.txt", "[" . date("Y-m-d H:i:s") . "] Le robot est inactif au démarrage.\n", FILE_APPEND);
}

?>