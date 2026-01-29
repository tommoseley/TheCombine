// components/sidecars/FeatureGrid.jsx
// Indigo side-car showing epic features

import { TRAY_CONFIG } from '../../data/constants.js';

const { GAP: TRAY_GAP } = TRAY_CONFIG;

export default function FeatureGrid({ features, epicName, nodeWidth, onClose }) {
    const useVertical = features.length > 6;
    const gridWidth = useVertical ? 240 : 320;
    
    return (
        <div 
            className="absolute top-0 bg-slate-900 border border-indigo-500/50 rounded-lg shadow-2xl tray-slide"
            style={{ left: nodeWidth + TRAY_GAP, width: gridWidth, boxShadow: '0 0 30px rgba(0,0,0,0.5)', zIndex: 1000 }}
        >
            {/* Connector line */}
            <div 
                className="absolute top-1/2 -translate-y-1/2 border-t-2 border-dashed border-indigo-500/60" 
                style={{ right: '100%', width: TRAY_GAP }} 
            />
            <div 
                className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-indigo-500" 
                style={{ right: '100%', marginRight: -4 }} 
            />
            
            {/* Header */}
            <div className="bg-indigo-500/10 border-b border-indigo-500/30 px-3 py-2 flex justify-between items-center">
                <span className="text-[9px] font-semibold text-indigo-400 uppercase tracking-wide">
                    Features — {epicName}
                </span>
                <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-sm leading-none">
                    &times;
                </button>
            </div>
            
            {/* Feature list */}
            <div className={'p-3 max-h-64 overflow-y-auto ' + (useVertical ? '' : 'grid grid-cols-2 gap-2')}>
                {features.map(f => {
                    const stateColor = f.state === 'complete' ? 'bg-emerald-500' : 
                                       f.state === 'active' ? 'bg-indigo-500' : 'bg-slate-600';
                    return (
                        <div 
                            key={f.id} 
                            className={'flex items-center gap-2 p-1.5 rounded hover:bg-slate-800/50 cursor-pointer ' + (useVertical ? 'mb-1' : '')}
                        >
                            <div className={'w-2 h-2 rounded-full flex-shrink-0 ' + stateColor} />
                            <span className="text-[10px] text-slate-300 truncate">{f.name}</span>
                        </div>
                    );
                })}
            </div>
            
            {/* Footer */}
            <div className="px-3 py-2 border-t border-slate-800 text-[9px] text-slate-500">
                {features.length} features • Click to expand
            </div>
        </div>
    );
}