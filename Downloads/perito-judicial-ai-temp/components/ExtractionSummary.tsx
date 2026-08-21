
import React from 'react';
import { ExtractionData, CustomTemplate } from '../types';
import { formatThousandSeparators, numberToExtenso } from '../services/numberUtils';
import { getSmartQuesitoAnswer } from '../services/quesitoUtils';
import { 
  Activity, 
  Bookmark, 
  FileSpreadsheet, 
  Scale, 
  Clock, 
  FileText,
  FileDown,
  DollarSign,
  Hash,
  Users,
  Sparkles,
  FileCode,
  Plus,
  Trash2,
  Tag
} from 'lucide-react';

interface ExtractionSummaryProps {
  data: ExtractionData | null;
  customTemplate: CustomTemplate | null;
  onUpdateData: (data: ExtractionData) => void;
  onExportCsv: () => void;
  onExportJson: () => void;
  onExportExcel: () => void;
  onExportWord: () => void;
  onExportCustomTemplate: () => void;
}

export const ExtractionSummary: React.FC<ExtractionSummaryProps> = ({ 
  data, 
  customTemplate,
  onUpdateData,
  onExportCsv, 
  onExportJson, 
  onExportExcel, 
  onExportWord,
  onExportCustomTemplate 
}) => {
  if (!data) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-full overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50">
          <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Activity size={18} className="text-slate-400" />
            Estrutura do Laudo
          </h2>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400 space-y-4">
          <FileSpreadsheet size={48} strokeWidth={1} className="text-slate-200" />
          <p className="text-xs">Aguardando comando <span className="font-bold text-blue-600">EXTRAIR</span> para mapear o processo.</p>
        </div>
      </div>
    );
  }

  const handleLaudoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateData({ ...data, Numero_Laudo: e.target.value });
  };

  const honorariosTemplate = `${data.Honorarios_Tipo} - ${data.Honorarios_Valor}, homologado em ${data.Honorarios_Homologacao_Data}, fls. ${data.Honorarios_Homologacao_Fls}`;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-full overflow-hidden">
      <div className="p-3 border-b border-slate-100 bg-slate-900 flex items-center justify-between gap-2">
        <h2 className="text-xs font-bold text-white flex items-center gap-1.5 truncate">
          <Scale size={16} className="text-blue-400 shrink-0" />
          <span className="truncate">Dossiê: {data.Autos.split('.')[0]}</span>
        </h2>
        <div className="flex items-center gap-1.5 shrink-0">
          <button 
            onClick={onExportCustomTemplate}
            className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-bold transition-all flex items-center gap-1 shadow-sm"
            title="Preencher e exportar mantendo o seu padrão/modelo personalizado"
          >
            <Sparkles size={12} />
            {customTemplate ? 'Meu Padrão' : 'Preencher {{}}'}
          </button>

          <div className="group relative">
            <button className="p-1.5 bg-slate-800 text-white rounded hover:bg-slate-700 transition-colors" title="Outros Formatos de Exportação">
              <FileDown size={14} />
            </button>
            <div className="absolute right-0 mt-2 w-44 bg-white border border-slate-200 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 py-1">
              <button onClick={onExportCustomTemplate} className="w-full text-left px-3 py-2 text-[10px] font-bold text-blue-700 bg-blue-50/60 hover:bg-blue-100 border-b border-slate-100 flex items-center gap-1.5">
                <FileCode size={12} /> NO SEU PADRÃO ({customTemplate ? customTemplate.type.toUpperCase() : 'TXT/DOCX'})
              </button>
              <button onClick={onExportWord} className="w-full text-left px-3 py-2 text-[10px] font-bold text-slate-600 hover:bg-blue-50 hover:text-blue-700 border-b border-slate-100">WORD PADRÃO (.docx)</button>
              <button onClick={onExportExcel} className="w-full text-left px-3 py-2 text-[10px] font-bold text-slate-600 hover:bg-green-50 hover:text-green-700 border-b border-slate-100">EXCEL (.xlsx)</button>
              <button onClick={onExportCsv} className="w-full text-left px-3 py-2 text-[10px] font-bold text-slate-600 hover:bg-slate-50 border-b border-slate-100">CSV (Mala Direta)</button>
              <button onClick={onExportJson} className="w-full text-left px-3 py-2 text-[10px] font-bold text-slate-600 hover:bg-slate-50">JSON</button>
            </div>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-5">
        <section className="space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <Hash size={12} /> Número do Laudo
          </h3>
          <div className="relative">
            <input 
              type="text" 
              value={data.Numero_Laudo} 
              onChange={handleLaudoChange}
              placeholder="Ex: LAUDO-2024-001"
              className={`w-full p-2.5 text-xs font-bold rounded border transition-all ${
                data.Numero_Laudo === 'INFORMAR' || !data.Numero_Laudo
                ? 'border-red-300 bg-red-50 text-red-600 placeholder:text-red-300' 
                : 'border-slate-200 bg-white text-slate-800'
              }`}
            />
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <Bookmark size={12} /> Identificação do Processo
          </h3>
          <div className="bg-slate-50 p-2 rounded border border-slate-100">
            <p className="text-[9px] text-slate-500 uppercase">Autos</p>
            <p className="text-xs font-bold text-slate-800 truncate">{data.Autos}</p>
          </div>
          <div className="bg-slate-50 p-2 rounded border border-slate-100">
            <p className="text-[9px] text-slate-500 uppercase">Objeto (Pontos Controvertidos)</p>
            <p className="text-xs text-slate-800 leading-snug font-medium italic">"{data.Objeto}"</p>
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <Users size={12} /> Quesitos e Assistentes
          </h3>
          <div className="bg-slate-900 p-3 rounded border border-slate-800 shadow-inner">
            <p className="text-[10px] text-blue-300 font-mono leading-relaxed">
              {data.Quesitos_Resumo_Formatado}
            </p>
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <Clock size={12} /> Nomeação e Cronograma
          </h3>
          <div className="bg-blue-50/50 p-2 rounded border border-blue-100 space-y-1">
            <p className="text-xs text-slate-800 font-medium">Nomeação: {data.Nomeacao_Data} - fls. {data.Nomeacao_Fls}</p>
            <p className="text-xs text-slate-700">Autoridade: {data.Autoridade}</p>
            <p className="text-xs text-slate-700">Início Formal: {data.Inicio_Data}, às {data.Inicio_Hora} ({data.Inicio_Tipo})</p>
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <DollarSign size={12} /> Honorários
          </h3>
          <div className="bg-green-50 p-2 rounded border border-green-100 space-y-1">
            <p className="text-[10px] font-bold text-green-800 uppercase">Fixação de Honorários:</p>
            <p className="text-xs text-slate-800 italic">{honorariosTemplate}</p>
            <p className="text-[10px] text-slate-600 mt-1 font-medium">{data.Honorarios_Resumo_Final}</p>
          </div>
        </section>

        <section className="space-y-2 bg-amber-50/60 p-2.5 rounded-lg border border-amber-200/80">
          <h3 className="text-[10px] font-bold text-amber-900 uppercase tracking-widest flex items-center gap-1.5">
            <FileSpreadsheet size={13} className="text-amber-600" /> Decisão Judicial, Extrato e Planilha
          </h3>
          
          <div className="space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[9px] font-bold text-amber-800 uppercase block mb-0.5">
                  Diferença Apurada Fev/1989 <span className="text-slate-400 font-mono font-normal">{`{{diferenca_valor}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Diferenca_Valor || ''} 
                  onChange={(e) => onUpdateData({ ...data, Diferenca_Valor: e.target.value })}
                  onBlur={(e) => {
                    const formatted = formatThousandSeparators(e.target.value);
                    if (formatted && formatted !== e.target.value) {
                      onUpdateData({ ...data, Diferenca_Valor: formatted });
                    }
                  }}
                  placeholder="Ex: 286,61"
                  className="w-full p-1.5 text-xs font-bold rounded border border-amber-200 bg-white text-amber-950 focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="text-[9px] font-bold text-emerald-800 uppercase block mb-0.5">
                  Saldo Credor (R$) <span className="text-slate-400 font-mono font-normal">{`{{saldo_credor}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Saldo_Credor || ''} 
                  onChange={(e) => {
                    const val = e.target.value;
                    const autoExtenso = numberToExtenso(val);
                    onUpdateData({ 
                      ...data, 
                      Saldo_Credor: val,
                      Saldo_Credor_Extenso: autoExtenso || data.Saldo_Credor_Extenso || ''
                    });
                  }}
                  onBlur={(e) => {
                    const val = e.target.value;
                    const formatted = formatThousandSeparators(val);
                    const autoExtenso = numberToExtenso(formatted || val);
                    onUpdateData({ 
                      ...data, 
                      Saldo_Credor: formatted || val,
                      Saldo_Credor_Extenso: autoExtenso || data.Saldo_Credor_Extenso || ''
                    });
                  }}
                  placeholder="Ex: R$ 15.420,50"
                  className="w-full p-1.5 text-xs font-bold rounded border border-emerald-300 bg-white text-emerald-950 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[9px] font-bold text-emerald-800 uppercase block mb-0.5">
                  Saldo Credor por Extenso <span className="text-slate-400 font-mono font-normal">{`{{saldo_credor_extenso}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Saldo_Credor_Extenso || numberToExtenso(data.Saldo_Credor || data.Diferenca_Valor) || ''} 
                  onChange={(e) => onUpdateData({ ...data, Saldo_Credor_Extenso: e.target.value })}
                  placeholder="Ex: quinze mil, quatrocentos e vinte reais e cinquenta centavos"
                  className="w-full p-1.5 text-xs rounded border border-emerald-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-medium"
                />
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-600 uppercase block mb-0.5">
                  Data Base de Atualização <span className="text-slate-400 font-mono font-normal">{`{{data_base}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Data_Base || ''} 
                  onChange={(e) => onUpdateData({ ...data, Data_Base: e.target.value })}
                  placeholder="Ex: julho de 2026"
                  className="w-full p-1.5 text-xs rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="text-[9px] font-bold text-slate-600 uppercase block mb-0.5">
                Resumo dos Quesitos / Assistentes <span className="text-slate-400 font-mono font-normal">{`{{quesitos_info}}`}</span>
              </label>
              <input 
                type="text" 
                value={data.Quesitos_Info || ''} 
                onChange={(e) => onUpdateData({ ...data, Quesitos_Info: e.target.value })}
                placeholder="Ex: Sim, a Requerente em fls. 120/125 e requerida em fls. 140/142."
                className="w-full p-1.5 text-xs rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[9px] font-bold text-slate-600 uppercase block mb-0.5">
                  Fls. Decisão Judicial <span className="text-slate-400 font-mono font-normal">{`{{decisao_fls}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Decisao_Fls || ''} 
                  onChange={(e) => onUpdateData({ ...data, Decisao_Fls: e.target.value })}
                  placeholder="Ex: 125/128"
                  className="w-full p-1.5 text-xs rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-600 uppercase block mb-0.5">
                  Fls. Extrato Bancário <span className="text-slate-400 font-mono font-normal">{`{{extrato_fls}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Extrato_Fls || ''} 
                  onChange={(e) => onUpdateData({ ...data, Extrato_Fls: e.target.value })}
                  placeholder="Ex: 45/47"
                  className="w-full p-1.5 text-xs rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2">
              <div>
                <label className="text-[9px] font-bold text-slate-600 uppercase block mb-0.5">
                  Fls. Decisão de Nomeação <span className="text-slate-400 font-mono font-normal">{`{{nomeacao_decisao_fls}}`}</span>
                </label>
                <input 
                  type="text" 
                  value={data.Nomeacao_Decisao_Fls || ''} 
                  onChange={(e) => onUpdateData({ ...data, Nomeacao_Decisao_Fls: e.target.value })}
                  placeholder="Ex: 88"
                  className="w-full p-1.5 text-xs rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-600 uppercase block mb-0.5">
                  Citação/Transcrição da Decisão Judicial <span className="text-slate-400 font-mono font-normal">{`{{decisao_citacao}}`}</span>
                </label>
                <textarea 
                  rows={3}
                  value={data.Decisao_Citacao || ''} 
                  onChange={(e) => onUpdateData({ ...data, Decisao_Citacao: e.target.value })}
                  placeholder="Ex: Determino a apuração das diferenças de expurgos inflacionários conforme tabela prática..."
                  className="w-full p-1.5 text-xs rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 leading-relaxed"
                />
              </div>
            </div>
          </div>
        </section>

        {/* SECTION: CAMPOS DIVERSOS / PERSONALIZADOS (GENERALIZAÇÃO UNIVERSAL PARA QUALQUER RAMO DE PERÍCIA) */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Tag size={12} className="text-indigo-500" /> Campos Diversos / Personalizados (Tags Universais)
            </h3>
            <button
              type="button"
              onClick={() => {
                const currentCustom = data.Campos_Personalizados || {};
                const count = Object.keys(currentCustom).length + 1;
                const newKey = `CAMPO_PERSONALIZADO_${count}`;
                onUpdateData({
                  ...data,
                  Campos_Personalizados: {
                    ...currentCustom,
                    [newKey]: ''
                  }
                });
              }}
              className="px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-[10px] font-bold rounded border border-indigo-200 transition-colors flex items-center gap-1"
            >
              <Plus size={11} />
              Adicionar Campo / Tag
            </button>
          </div>

          <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200/80 space-y-2">
            <p className="text-[10px] text-slate-500 italic">
              Adicione qualquer variável técnica específica do seu tipo de perícia (ex: <code className="bg-slate-100 px-1 py-0.5 rounded text-indigo-600 font-mono font-semibold">TAXA_JUROS</code>, <code className="bg-slate-100 px-1 py-0.5 rounded text-indigo-600 font-mono font-semibold">VALOR_CONTRATO</code>, <code className="bg-slate-100 px-1 py-0.5 rounded text-indigo-600 font-mono font-semibold">GRAU_INSALUBRIDADE</code>, <code className="bg-slate-100 px-1 py-0.5 rounded text-indigo-600 font-mono font-semibold">AREA_IMOVEL</code>). As tags <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">{`{{NOME_DA_TAG}}`}</code> serão substituídas automaticamente nos modelos do Word.
            </p>

            {(!data.Campos_Personalizados || Object.keys(data.Campos_Personalizados).length === 0) ? (
              <div className="text-center py-3 border border-dashed border-slate-200 rounded text-[11px] text-slate-400">
                Nenhum campo personalizado adicionado. Clique acima para criar tags livres para seu modelo.
              </div>
            ) : (
              <div className="space-y-2">
                {Object.entries(data.Campos_Personalizados).map(([customKey, customVal]) => (
                  <div key={customKey} className="flex items-center gap-2 bg-white p-2 rounded border border-slate-200 shadow-sm">
                    <div className="w-1/3">
                      <label className="text-[8px] font-bold text-indigo-600 uppercase block">Nome da Tag / Variável</label>
                      <input
                        type="text"
                        value={customKey}
                        onChange={(e) => {
                          const newK = e.target.value.replace(/[^a-zA-Z0-9_]/g, '_').toUpperCase();
                          const updated = { ...(data.Campos_Personalizados || {}) };
                          delete updated[customKey];
                          updated[newK] = customVal;
                          onUpdateData({ ...data, Campos_Personalizados: updated });
                        }}
                        placeholder="Ex: TAXA_JUROS"
                        className="w-full p-1 text-xs font-mono font-bold text-slate-700 bg-slate-50 rounded border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                      <span className="text-[8px] text-slate-400 font-mono block mt-0.5">{`{{${customKey.toLowerCase()}}}`}</span>
                    </div>

                    <div className="flex-1">
                      <label className="text-[8px] font-bold text-slate-500 uppercase block">Valor do Campo</label>
                      <input
                        type="text"
                        value={customVal}
                        onChange={(e) => {
                          const updated = { ...(data.Campos_Personalizados || {}) };
                          updated[customKey] = e.target.value;
                          onUpdateData({ ...data, Campos_Personalizados: updated });
                        }}
                        placeholder="Ex: 1,5% ao mês ou R$ 50.000,00"
                        className="w-full p-1 text-xs text-slate-800 rounded border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        const updated = { ...(data.Campos_Personalizados || {}) };
                        delete updated[customKey];
                        onUpdateData({ ...data, Campos_Personalizados: updated });
                      }}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors self-center mt-2"
                      title="Excluir campo"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <FileText size={12} /> Quesitos e Análise Técnica de Respostas
          </h3>
          <div className="space-y-4">
            {['Juizo', 'Requerente', 'Requerido'].map((key) => {
              const quesitos = (data.Quesitos_Detalhados[key as keyof typeof data.Quesitos_Detalhados] as string[]) || [];
              const respostas = (data.Quesitos_Detalhados[`Respostas_${key}` as keyof typeof data.Quesitos_Detalhados] as string[]) || [];
              const ref = data.Quesitos_Detalhados[`Referencia_${key}` as keyof typeof data.Quesitos_Detalhados] as string;
              
              if (!quesitos || quesitos.length === 0) return null;

              return (
                <div key={key} className="border-l-2 border-slate-200 pl-3 space-y-2">
                  <div className="mb-1">
                    <p className="text-[10px] font-bold text-slate-700 uppercase inline">
                      {key === 'Juizo' ? 'Pelo Juízo' : key === 'Requerente' ? 'Pela Parte Requerente' : 'Pela Parte Requerida'}
                    </p>
                    {ref && <span className="text-[9px] text-slate-400 font-medium italic ml-1">({ref})</span>}
                  </div>
                  <div className="space-y-3 mt-1">
                    {quesitos.map((q, idx) => {
                      const ans = getSmartQuesitoAnswer(q, respostas[idx], data);
                      const isExtra = ans.toLowerCase().includes('extra escopo') || ans.toLowerCase().includes('prejudicado') || ans.toLowerCase().includes('matéria de direito');

                      return (
                        <div key={`${key}-quesito-${idx}-${q.substring(0, 20)}`} className="bg-slate-50 p-2 rounded border border-slate-200 space-y-1.5">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-[10px] font-semibold text-slate-800 leading-snug">
                              <span className="text-blue-600 font-bold mr-1">{idx + 1}.</span> {q}
                            </p>
                            <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded whitespace-nowrap ${
                              isExtra ? 'bg-amber-100 text-amber-800 border border-amber-300' : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            }`}>
                              {isExtra ? 'Extra Escopo' : 'Escopo Técnico'}
                            </span>
                          </div>

                          <div>
                            <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Resposta Pericial</label>
                            <textarea
                              rows={2}
                              value={ans}
                              onChange={(e) => {
                                const newAnsArray = [...respostas];
                                newAnsArray[idx] = e.target.value;
                                onUpdateData({
                                  ...data,
                                  Quesitos_Detalhados: {
                                    ...data.Quesitos_Detalhados,
                                    [`Respostas_${key}`]: newAnsArray
                                  }
                                });
                              }}
                              className="w-full p-1 text-[10px] rounded border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 leading-snug"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
};
