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

    # Construct the merged header
    merged_headers = ['query']
    if eggnog_headers:
        merged_headers += [eggnog_mapping[h] for h in eggnog_headers if h != 'query']
    if foldseek_headers:
        merged_headers += [foldseek_mapping[h] for h in foldseek_headers if h != 'query']

    # EggNOG and Foldseek don't always report the same query ID format
    # (e.g. one may include extra suffixes/prefixes the other doesn't), so
    # a Foldseek query is matched to an EggNOG query by substring
    # containment rather than exact equality. This is a full outer join:
    # matched pairs become one row; EggNOG-only and Foldseek-only queries
    # are each kept as their own row (with the other side's columns empty).
    sorted_eggnog_queries = sorted(eggnog_data)
    fs_to_egg = {}
    unmatched_fs = []
    for fs_query in sorted(foldseek_data):
        egg_query = next((eq for eq in sorted_eggnog_queries if fs_query in eq), None)
        if egg_query is None:
            unmatched_fs.append(fs_query)
        else:
            fs_to_egg[fs_query] = egg_query

    egg_to_fs = {egg_query: fs_query for fs_query, egg_query in fs_to_egg.items()}

    if unmatched_fs:
        print(f"[WARN] {len(unmatched_fs)} Foldseek query ID(s) could not be mapped "
              f"to an EggNOG query ID and were kept as separate rows.")

    merged_rows = []
    for query in sorted_eggnog_queries:
        egg_row = eggnog_data.get(query, {})
        fs_row = foldseek_data.get(egg_to_fs.get(query), {})

        merged_row = {'query': query}
        for h in eggnog_headers:
            if h != 'query':
                merged_row[eggnog_mapping[h]] = egg_row.get(h, '')
        for h in foldseek_headers:
            if h != 'query':
                merged_row[foldseek_mapping[h]] = fs_row.get(h, '')

        merged_rows.append(merged_row)

    for fs_query in unmatched_fs:
        fs_row = foldseek_data.get(fs_query, {})

        merged_row = {'query': fs_query}
        for h in eggnog_headers:
            if h != 'query':
                merged_row[eggnog_mapping[h]] = ''
        for h in foldseek_headers:
            if h != 'query':
                merged_row[foldseek_mapping[h]] = fs_row.get(h, '')

        merged_rows.append(merged_row)

    return merged_headers, merged_rows
