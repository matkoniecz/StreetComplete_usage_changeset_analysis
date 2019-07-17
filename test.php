<?php
//from https://www.w3schools.com/Php/php_xml_simplexml_read.asp
//TODO in real code: log errors
$myXMLData =
"<?xml version='1.0' encoding='UTF-8'?>
<note>
<to>Tove</to>
<from>Jani</from>
<heading>Reminder</heading>
<body>Don't forget me this weekend!</body>
</note>";

$xml=simplexml_load_string($myXMLData) or die("Error: Cannot create object");
print_r($xml);

// https://wiki.openstreetmap.org/wiki/API_v0.6
// https://www.openstreetmap.org/api/0.6/changeset/72280172/download
// https://php.net/manual/en/book.curl.php
// https://stackoverflow.com/questions/3062324/what-is-curl-in-php
// https://www.php.net/manual/en/curl.examples-basic.php
$ch = curl_init("https://www.openstreetmap.org/api/0.6/changeset/72280172/download");
$fp = fopen("api_response.xml", "w");

curl_setopt($ch, CURLOPT_FILE, $fp);
curl_setopt($ch, CURLOPT_HEADER, 0);

curl_exec($ch);
curl_close($ch);
fclose($fp);

// database
// https://code.tutsplus.com/tutorials/php-database-access-are-you-doing-it-correctly--net-25338
// https://www.w3schools.com/PHP/php_mysql_create.asp
?>
