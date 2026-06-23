import csv

def read_tsv(filepath):
    data = {}
    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        headers = reader.fieldnames
        for row in reader:
            query = row.get('query')
            if query:
                data[query] = row
    return data, headers

def create_header_mapping(headers, prefix):
    return {h: h if h == 'query' else f"{prefix}_{h}" for h in headers}

def merge_data(eggnog_data, eggnog_headers, foldseek_data, foldseek_headers):
    eggnog_mapping = create_header_mapping(eggnog_headers, "eggnog")
    foldseek_mapping = create_header_mapping(foldseek_headers, "foldseek")

    # EggNOG and Foldseek don't always report the same query ID format
    # (e.g. one may include extra suffixes/prefixes the other doesn't), so
    # match a Foldseek query to an EggNOG query by substring containment
    # rather than exact equality. Foldseek queries with no match are kept
    # (not dropped) as their own rows, appended after the EggNOG-based rows.
    sorted_eggnog_queries = sorted(eggnog_data)
    foldseek_to_eggnog = {}
    unmatched_foldseek = []
    for fs_query in foldseek_data:
        match = next((egg_query for egg_query in sorted_eggnog_queries if fs_query in egg_query), None)
        if match:
            foldseek_to_eggnog[fs_query] = match
        else:
            unmatched_foldseek.append(fs_query)

    if unmatched_foldseek:
        print(f"[WARN] {len(unmatched_foldseek)} Foldseek query ID(s) could not be mapped "
              f"to an EggNOG query ID and were kept as separate rows.")

    eggnog_to_foldseek = {egg_query: fs_query for fs_query, egg_query in foldseek_to_eggnog.items()}

    # Construct the merged header
    merged_headers = ['query']
    if eggnog_headers:
        merged_headers += [eggnog_mapping[h] for h in eggnog_headers if h != 'query']
    if foldseek_headers:
        merged_headers += [foldseek_mapping[h] for h in foldseek_headers if h != 'query']

    # Merge rows: one per EggNOG query (with matched Foldseek data, if any),
    # followed by any unmatched Foldseek queries (with empty EggNOG data).
    merged_rows = []
    for query in sorted_eggnog_queries:
        merged_row = {'query': query}
        egg_row = eggnog_data.get(query, {})
        fs_row = foldseek_data.get(eggnog_to_foldseek.get(query), {})

        for h in eggnog_headers:
            if h != 'query':
                merged_row[eggnog_mapping[h]] = egg_row.get(h, '')
        for h in foldseek_headers:
            if h != 'query':
                merged_row[foldseek_mapping[h]] = fs_row.get(h, '')

        merged_rows.append(merged_row)

    for fs_query in sorted(unmatched_foldseek):
        merged_row = {'query': fs_query}
        fs_row = foldseek_data.get(fs_query, {})

        for h in eggnog_headers:
            if h != 'query':
                merged_row[eggnog_mapping[h]] = ''
        for h in foldseek_headers:
            if h != 'query':
                merged_row[foldseek_mapping[h]] = fs_row.get(h, '')

        merged_rows.append(merged_row)

    return merged_headers, merged_rows
