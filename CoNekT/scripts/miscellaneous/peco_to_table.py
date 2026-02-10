#!/usr/bin/env python3

with open('peco.obo') as f:

    current_term = 0
    printed_to_file = 1
    peco_id = ''
    peco_name = ''

    for line in f:
        # Skip empty
        line = line.rstrip('\n')

        if not line:
            if (not printed_to_file) and peco_id and peco_name:
                print(f'{peco_id}\t{peco_name}\tno_peco_definition')
            current_term = 0
            peco_id = ''
            peco_name = ''
            peco_def = ''
            printed_to_file = 0
            continue

        if line == "[Term]":

            if current_term:
                print(f'Something wrong. Current term ({current_term}) exists.')
                exit(1)
            current_term = 1

        if line.startswith('id: PECO:') and current_term:
                peco_id = line.replace('id: ', '')

        if line.startswith("name: ") and current_term:

            if peco_id:
                peco_name = line.replace('name: ', '')
            else:
                print(f'Something wrong with PECO ID {peco_name}')

        if line.startswith("def: ") and current_term:

            if peco_id:
                #and peco_name:
                peco_def = line.replace('def: ', '')
                print(f'{peco_id}\t{peco_name}\t{peco_def}')
                printed_to_file = 1
                peco_id = ''
                peco_name = ''
                peco_def = ''
                current_term = 0
            else:
                print(f'Something is wrong with PECO ID {peco_id}')
