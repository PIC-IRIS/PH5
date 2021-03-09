pn3 is the previous PH5 data version which has no sample_rate_multiplier_i (srm) column in the structure.

array_das: both array_t and das_t have no arm

das: only das_t has no sum (array_t is always checked first. This table has array_t with normal srm so that srm in das_t can be checked) 