<?php
// assumptions
// changesets are formatted as follows:
// either (1)
// line begins with 
// "<changeset" and ends with "/>"
// and it is a changeset without tags
// or (2)
// line begins with '<changeset' and ends with '">'
// tags, one in each line follows
// ends with line including '</changeset>' as sole nonwhitespace text
// applies

function value_of_key($line, $tag) {
    $left_stripped = str_replace("<tag k=\"" . $tag . "\" v=\"", "", $line);
    return str_replace('"/>', '', $left_stripped);
}

function quest_tag_to_identifier($line) {
    return value_of_key($line, "StreetComplete:quest_type");
}

function created_by_tag_to_identifier($line) {
    return value_of_key($line, "created_by");
}

// from https://www.php.net/manual/en/function.substr-compare.php
function str_begins($haystack, $needle) {
    return 0 === substr_compare($haystack, $needle, 0, strlen($needle));
}
  
function str_ends($haystack,  $needle) {
    return 0 === substr_compare($haystack, $needle, -strlen($needle));
}

function contains_substr($mainStr, $str, $loc = false) {
    if ($loc === false) return (strpos($mainStr, $str) !== false);
    if (strlen($mainStr) < strlen($str)) return false;
    if (($loc + strlen($str)) > strlen($mainStr)) return false;
    return (strcmp(substr($mainStr, $loc, strlen($str)), $str) == 0);
}

function get_changes_number($changeset_header) {
    if (preg_match("/num_changes=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return 0;
    }
}

function get_quest_type($changeset_header) {
    if (preg_match("/v=\"([^\"]+)\"/", $changeset_header, $matches)) {
        return $matches[1];
    } else {
        return NULL;
    }
}

function get_changeset_id($changeset_header) {
    if (preg_match("/ id=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return -1;
    }
}

function get_uid($changeset_header) {
    if (preg_match("/ uid=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return -1;
    }
}

function get_changeset_creation_date($changeset_header) {
    if (preg_match("/ created_at=\"([^\"]+)\"/", $changeset_header, $matches)) {
        return $matches[1];
    } else {
        return -1;
    }
}

?>
