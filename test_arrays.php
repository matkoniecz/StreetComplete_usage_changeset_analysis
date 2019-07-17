<?php
$popularity = array();
$popularity["aaaaa"] = 1;
$popularity["b"] = 1;

if (isset($popularity["c"])) {
    $popularity["c"] += 1;
} else {
    $popularity["c"] = 0;
}

if (isset($popularity["b"])) {
    $popularity["b"] += 1;
} else {
    $popularity["b"] = 0;
}

var_dump($popularity);
?>