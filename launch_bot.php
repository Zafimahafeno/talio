<?php
$pythonScript = 'mt5_bot.py';
shell_exec("python3 $pythonScript > /dev/null 2>/dev/null &");
echo json_encode(['status' => 'started']);
?>
