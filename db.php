<?php
$host = 'mysql-mahafeno.alwaysdata.net';
$db   = 'mahafeno_trading';
$user = 'mahafeno';
$pass = 'antso0201'; // mets ton mot de passe MySQL ici
$charset = 'utf8mb4';

$dsn = "mysql:host=$host;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
];

try {
     $pdo = new PDO($dsn, $user, $pass, $options);
} catch (\PDOException $e) {
     die("Erreur de connexion à la base de données : " . $e->getMessage());
}
?>
