import mido
import numpy as np
import random
import os

# ==========================================
# PASSO 1: EXTRAÇÃO DE DADOS MIDI
# ==========================================
def extrair_dados_midi(caminho_do_arquivo):
    arquivo_midi = mido.MidiFile(caminho_do_arquivo)
    sequencia_notas = []
    sequencia_ritmos = []
    
    for faixa in arquivo_midi.tracks:
        tempo_acumulado = 0
        nota_ativa = None
        
        for msg in faixa:
            tempo_acumulado += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                if nota_ativa is not None and tempo_acumulado > 0:
                    sequencia_notas.append(nota_ativa)
                    sequencia_ritmos.append(tempo_acumulado)
                    tempo_acumulado = 0
                nota_ativa = msg.note
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if nota_ativa is not None and msg.note == nota_ativa:
                    sequencia_notas.append(nota_ativa)
                    sequencia_ritmos.append(tempo_acumulado)
                    tempo_acumulado = 0
                    nota_ativa = None
                    
    return sequencia_notas, sequencia_ritmos

# ==========================================
# PASSO 2: CÁLCULO DE PROBABILIDADES (MÚLTIPLOS RITMOS)
# ==========================================
def analisar_estados_compostos_complexos(notas, ritmos_brutos):
    """
    Mapeia a música aceitando QUALQUER quantidade de figuras rítmicas diferentes.
    Cada estado composto é um par (Nota, Duracao_em_Ticks).
    """
    # Em músicas reais, pequenas variações de gravação humana podem acontecer.
    # Arredondamos os ticks para os múltiplos de 10 mais próximos para agrupar notas idênticas.
    ritmos_limpos = [int(round(r / 10.0)) * 10 for r in ritmos_brutos]
    
    # Cria a sequência de estados compostos: (Nota, Ticks)
    sequencia_estados = [(notas[i], ritmos_limpos[i]) for i in range(len(notas))]
    
    # Identifica todos os estados únicos (combinações de nota e ritmo que existem na peça)
    estados_unicos = sorted(list(set(sequencia_estados)))
    num_estados = len(estados_unicos)
    
    estado_para_idx = {estado: i for i, estado in enumerate(estados_unicos)}
    
    # Monta a matriz de contagem
    matriz_contagem = np.zeros((num_estados, num_estados))
    for i in range(len(sequencia_estados) - 1):
        atual = sequencia_estados[i]
        proximo = sequencia_estados[i+1]
        
        linha = estado_para_idx[atual]
        coluna = estado_para_idx[proximo]
        matriz_contagem[linha][coluna] += 1
        
    # Normaliza para obter as probabilidades de transição
    matriz_probabilidade = np.zeros((num_estados, num_estados))
    for i in range(num_estados):
        soma_linha = np.sum(matriz_contagem[i])
        if soma_linha > 0:
            matriz_probabilidade[i] = matriz_contagem[i] / soma_linha
            
    return matriz_probabilidade, estados_unicos

# ==========================================
# PASSO 3: GERADOR ESTOCÁSTICO
# ==========================================
def gerar_nova_melodia(matriz_probabilidade, estados_unicos, estado_inicial, tamanho_melodia):
    estado_para_idx = {estado: i for i, estado in enumerate(estados_unicos)}
    
    if estado_inicial not in estado_para_idx:
        estado_atual = estados_unicos[0]
    else:
        estado_atual = estado_inicial
        
    melodia_gerada = [estado_atual]
    
    for _ in range(tamanho_melodia - 1):
        idx_current = estado_para_idx[estado_atual]
        probabilidades_linha = matriz_probabilidade[idx_current]
        
        # CORREÇÃO: Verifica se a linha é um "beco sem saída" (soma dos pesos é zero)
        if np.sum(probabilidades_linha) == 0:
            # Se for um beco sem saída, escolhe QUALQUER estado da música para continuar
            proximo_estado = random.choice(estados_unicos)
        else:
            # Se a linha tiver probabilidades válidas, faz o sorteio normal de Markov
            proximo_estado = random.choices(estados_unicos, weights=probabilidades_linha, k=1)[0]
            
        melodia_gerada.append(proximo_estado)
        estado_atual = proximo_estado
        
    return melodia_gerada

# ==========================================
# PASSO 4: EXPORTAR PARA NOVO ARQUIVO MIDI
# ==========================================
def salvar_midi_complexo(melodia_gerada, caminho_saida="saida.mid"):
    """
    Reconstrói o arquivo MIDI injetando a duração exata em ticks que foi associada
    a cada nota durante o mapeamento de estados compostos.
    """
    novo_midi = mido.MidiFile()
    nova_faixa = mido.MidiTrack()
    novo_midi.tracks.append(nova_faixa)
    
    for nota, duracao_ticks in melodia_gerada:
        # Garante que tempos zerados acidentais não quebrem a reprodução
        tempo_nota = max(duracao_ticks, 20)
        
        # Ativa a nota no canal
        nova_faixa.append(mido.Message('note_on', note=nota, velocity=64, time=0))
        # Mantém a nota soando pelos ticks exatos sorteados pelo modelo
        nova_faixa.append(mido.Message('note_off', note=nota, velocity=0, time=tempo_nota))
        
    novo_midi.save(caminho_saida)
    print(f"[PASSO 4] Arquivo complexo '{caminho_saida}' gerado e salvo com sucesso!")

# ==========================================
# EXECUÇÃO DO FLUXO COMPLETO
# ==========================================
if __name__ == "__main__":
    # COLOQUE O SEU ARQUIVO COMPLEXO AQUI (ex: uma música de Bach, Chopin ou Jazz)
    arquivo_teste = "entrada.mid" 
    
    if os.path.exists(arquivo_teste):
        print(f"--- Iniciando Processo de Cadeia de Markov (Modo Complexo) ---")
        
        # PASSO 1: Extração
        notas_brutas, ritmos_brutos = extrair_dados_midi(arquivo_teste)
        quantidade_original = len(notas_brutas)
        print(f"[PASSO 1] Total de notas detectadas na partitura: {quantidade_original}")
        
        # PASSO 2: Análise Multirrítmica
        matriz_p, lista_estados = analisar_estados_compostos_complexos(notas_brutas, ritmos_brutos)
        print(f"[PASSO 2] Matriz gerada. Total de combinações únicas (Nota, Ritmo): {len(lista_estados)}")
        
        # PASSO 3: Geração Estocástica Proporcional
        # Iniciamos com o primeiro par real extraído da música
        primeiro_ritmo_limpo = int(round(ritmos_brutos[0] / 10.0)) * 10
        estado_inicial_escolhido = (notas_brutas[0], primeiro_ritmo_limpo)
        
        print(f"[PASSO 3] Sorteando nova melodia com {quantidade_original} notas...")
        nova_sequencia = gerar_nova_melodia(matriz_p, lista_estados, estado_inicial_escolhido, tamanho_melodia=quantidade_original)
        
        # PASSO 4: Exportação de Áudio
        salvar_midi_complexo(nova_sequencia, caminho_saida="saida.mid")
        
        print("\nProcesso concluído! Seu novo arquivo 'saida.mid' preservou toda a estrutura rítmica complexa.")
    else:
        print(f"Aviso: Coloque o arquivo '{arquivo_teste}' na mesma pasta para executar o teste.")