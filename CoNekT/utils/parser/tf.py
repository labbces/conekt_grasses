def parse_tf_txt(filename):
    """
    Parser para arquivos de anotação de Transcription Factors (TFs).
    Espera um arquivo tab-delimitado com as colunas: Gene, Family, Tipo.
    Retorna uma lista de dicionários: {gene, family, tipo}
    """
    tfs = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith('gene'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            gene, family, tipo = parts[0], parts[1], parts[2]
            tfs.append({'gene': gene, 'family': family, 'tipo': tipo})
    return tfs 