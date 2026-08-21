
import React from 'react';
import { ChatMessage } from '../types';
import { Bot, User, FileOutput, CheckCircle, AlertTriangle } from 'lucide-react';

interface ChatMessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export const ChatMessageList: React.FC<ChatMessageListProps> = ({ messages, isLoading }) => {
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
      {messages.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-slate-400 max-w-sm mx-auto text-center space-y-4">
          <Bot size={48} className="text-slate-200" />
          <div>
            <p className="text-sm font-medium text-slate-500">Pronto para a análise pericial</p>
            <p className="text-xs">Carregue as peças processuais e digite <code className="bg-slate-100 px-1 rounded text-blue-600 font-bold">EXTRAIR</code> para começar.</p>
          </div>
        </div>
      )}
      
      {messages.map((msg) => (
        <div key={`${msg.role}-${msg.timestamp.getTime()}-${messages.indexOf(msg)}`} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
            msg.role === 'user' ? 'bg-slate-700' : 'bg-blue-600'
          }`}>
            {msg.role === 'user' ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
          </div>
          
          <div className={`max-w-[85%] rounded-2xl p-4 shadow-sm border ${
            msg.role === 'user' 
              ? 'bg-white border-slate-200 rounded-tr-none' 
              : 'bg-blue-50 border-blue-100 rounded-tl-none'
          }`}>
            <div className="prose prose-sm max-w-none prose-slate">
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                {msg.text.split(/```json[\s\S]*?```/).map((part, i, arr) => (
                  <React.Fragment key={`text-${i}-${part.length}`}>{part}</React.Fragment>
                ))}
              </div>
            </div>
            
            {msg.isExtraction && msg.data && (
              <div className="mt-4 pt-4 border-t border-blue-200 flex flex-wrap gap-2">
                <span className="inline-flex items-center px-2 py-1 rounded bg-green-100 text-green-700 text-[10px] font-bold uppercase tracking-wider">
                  <CheckCircle size={10} className="mr-1" /> Dados Estruturados OK
                </span>
                <span className="inline-flex items-center px-2 py-1 rounded bg-blue-100 text-blue-700 text-[10px] font-bold uppercase tracking-wider">
                  <FileOutput size={10} className="mr-1" /> PDF Rastreado
                </span>
              </div>
            )}
            
            <p className="text-[10px] text-slate-400 mt-2">
              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
      ))}
      
      {isLoading && (
        <div className="flex gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 animate-pulse">
            <Bot size={16} className="text-white" />
          </div>
          <div className="bg-blue-50 border border-blue-100 rounded-2xl rounded-tl-none p-4 shadow-sm flex items-center gap-2">
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-xs text-blue-500 font-medium italic">Analisando peças processuais...</span>
          </div>
        </div>
      )}
    </div>
  );
};
