# Índice Melão (Versão Local)

Aplicativo desktop para análise de criptomoedas, cálculo de indicadores e visualização de dados, com filtros avançados e interface moderna em modo escuro.

## Funcionalidades

- **Interface desktop (Tkinter + CustomTkinter)**
- **Upload de dados**: Importe arquivos `.xlsx` com cotações de criptomoedas.
- **Atualização automática**: Busque e atualize cotações das principais criptos.
- **Configuração de inflação**: Ajuste taxas de inflação para diferentes períodos.
- **Filtros avançados**: Filtre por índice, Hurst, rentabilidade, MDD, ativo e períodos.
- **Visualização gráfica**: Plote gráficos interativos dos ativos selecionados.
- **Exportação**: Exporte resultados filtrados para Excel.
- **Visual escuro e responsivo**: Interface agradável e intuitiva.

## Como usar

1. **Instale as dependências**  
   No terminal, execute:
   ```bash
   pip install -r requirements.txt
   ```

2. **Execute o aplicativo**
   ```bash
   python main.py
   ```

3. **Utilize a interface**
   - Carregue seus dados ou atualize as criptomoedas.
   - Configure inflação conforme necessário.
   - Use os filtros para refinar sua análise.
   - Plote gráficos e exporte resultados conforme desejar.

## Estrutura do Projeto

```
IndicadoresCripto/
│
├── Local/
│   └── main.py           # Código principal da versão desktop (Tkinter)
├── requirements.txt      # Dependências Python
├── inflation.json        # Configurações de inflação
├── crypto_cache.db       # Banco de dados SQLite (gerado automaticamente)
├── ...
```

## Observação

> **A versão Web (Dash) está em desenvolvimento e será lançada em breve!**