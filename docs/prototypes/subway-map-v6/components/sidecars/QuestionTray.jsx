// components/sidecars/QuestionTray.jsx
// Amber side-car for operator input

import { TRAY_CONFIG } from '../../data/constants.js';

const { GAP: TRAY_GAP, WIDTH: TRAY_WIDTH } = TRAY_CONFIG;

export default function QuestionTray({ questions, nodeWidth, onSubmit, onClose }) {
    const [answers, setAnswers] = React.useState({});
    const allAnswered = questions.filter(q => q.required).every(q => answers[q.id]);
    
    return (
        <div 
            className="absolute top-0 bg-slate-900 border border-amber-500/50 rounded-lg shadow-2xl tray-slide"
            style={{ left: nodeWidth + TRAY_GAP, width: TRAY_WIDTH, boxShadow: '0 0 30px rgba(0,0,0,0.5)', zIndex: 1000 }}
        >
            {/* Connector line */}
            <div 
                className="absolute top-1/2 -translate-y-1/2 border-t-2 border-dashed border-amber-500/60" 
                style={{ right: '100%', width: TRAY_GAP }} 
            />
            <div 
                className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-amber-500" 
                style={{ right: '100%', marginRight: -4 }} 
            />
            
            {/* Header */}
            <div className="bg-amber-500/10 border-b border-amber-500/30 px-3 py-2 flex justify-between items-center">
                <span className="text-[9px] font-semibold text-amber-400 uppercase tracking-wide">
                    Operator Input Required
                </span>
                <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-sm leading-none">
                    &times;
                </button>
            </div>
            
            {/* Questions */}
            <div className="p-3 space-y-3 max-h-64 overflow-y-auto">
                {questions.map(q => (
                    <div key={q.id}>
                        <label className="block text-[10px] text-slate-400 mb-1">
                            {q.text} {q.required && <span className="text-amber-500">*</span>}
                        </label>
                        <input 
                            type="text"
                            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-amber-500 focus:outline-none"
                            value={answers[q.id] || ''}
                            onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                        />
                    </div>
                ))}
            </div>
            
            {/* Submit button */}
            <div className="p-3 border-t border-slate-800">
                <button 
                    className={'w-full py-2 rounded text-xs font-medium transition-colors ' + 
                        (allAnswered 
                            ? 'bg-amber-500 text-slate-900 hover:bg-amber-400' 
                            : 'bg-slate-700 text-slate-500 cursor-not-allowed')}
                    disabled={!allAnswered}
                    onClick={() => onSubmit(answers)}
                >
                    Submit & Continue
                </button>
            </div>
        </div>
    );
}