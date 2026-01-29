// components/nodes/DocumentNode.jsx
// Main station UI component for spine documents and epics

import { getColors } from '../../data/constants.js';
import StationDots from './StationDots.jsx';
import QuestionTray from '../sidecars/QuestionTray.jsx';
import FeatureGrid from '../sidecars/FeatureGrid.jsx';

export default function DocumentNode({ data, Handle, Position }) {
    const level = data.level || 1;
    const isL1 = level === 1;
    const colors = getColors(data.state);
    const isExpanded = data.isExpanded;
    const expandType = data.expandType;
    
    // Determine what can be shown
    const hasQuestions = data.questions?.length > 0;
    const hasFeatures = data.features?.length > 0;
    const needsInput = data.stations?.some(s => s.needs_input);
    const showStations = data.state === 'active' && data.stations;
    
    // State-based styling
    const stateClass = data.state === 'active' ? 'node-active' : '';
    const borderColor = data.state === 'active' ? 'border-indigo-500' : 
                        data.state === 'stabilized' ? 'border-emerald-500/50' : 'border-slate-700';
    
    // Header colors by level
    const headerBg = isL1 ? 'bg-emerald-500/10' : 'bg-indigo-500/10';
    const headerBorder = isL1 ? 'border-emerald-500/30' : 'border-indigo-500/30';
    const headerText = isL1 ? 'text-emerald-400' : 'text-indigo-400';
    const levelLabel = isL1 ? 'DOCUMENT' : 'EPIC';
    
    return (
        <div className="relative">
            <Handle type="target" position={Position.Top} className="!opacity-0" style={{left: '15%'}} />
            
            <div 
                className={`bg-slate-900 rounded-lg border ${borderColor} ${stateClass} overflow-hidden`}
                style={{ width: data.width, minHeight: data.height }}
            >
                {/* Header bar */}
                <div className={`${headerBg} border-b ${headerBorder} px-3 py-1.5 flex items-center justify-between`}>
                    <div className="flex items-center gap-2">
                        <span className={`text-[8px] font-bold ${headerText} uppercase tracking-wider`}>
                            {levelLabel}
                        </span>
                        <span className="text-[10px] text-slate-300 font-medium">{data.name}</span>
                    </div>
                    <span className={`text-[8px] px-1.5 py-0.5 rounded ${data.intent === 'mandatory' ? 'bg-slate-700 text-slate-400' : 'bg-slate-800 text-slate-500'}`}>
                        {data.intent?.toUpperCase()}
                    </span>
                </div>
                
                {/* Body */}
                <div className="p-3">
                    <div className="flex items-center gap-2">
                        <div 
                            className="rounded-full flex-shrink-0"
                            style={{ 
                                width: isL1 ? 24 : 18, 
                                height: isL1 ? 24 : 18, 
                                backgroundColor: colors.bg 
                            }}
                        />
                        <div className="flex-1 min-w-0">
                            <span className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: colors.text }}>
                                {data.state}
                            </span>
                            {isL1 && data.desc && (
                                <p className="text-[9px] text-slate-500 mt-0.5 truncate">{data.desc}</p>
                            )}
                        </div>
                    </div>
                    
                    {/* Station progress */}
                    {showStations && <StationDots stations={data.stations} />}
                    
                    {/* Action buttons */}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                        {/* View Document button for stabilized L1 */}
                        {isL1 && data.state === 'stabilized' && (
                            <button className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-[9px] hover:bg-emerald-500/30 transition-colors">
                                View Document
                            </button>
                        )}
                        
                        {/* Answer Questions button */}
                        {needsInput && hasQuestions && !isExpanded && (
                            <button 
                                className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-[9px] hover:bg-amber-500/30 transition-colors amber-pulse"
                                onClick={(e) => { e.stopPropagation(); data.onExpand?.(data.id, 'questions'); }}
                            >
                                Answer Questions
                            </button>
                        )}
                        
                        {/* Features button for L2 */}
                        {!isL1 && hasFeatures && (
                            isExpanded && expandType === 'features' ? (
                                <span className="text-[9px] text-indigo-400">
                                    {data.features.length} features expanded
                                </span>
                            ) : (
                                <button 
                                    className="px-2 py-1 bg-slate-800 text-slate-400 rounded text-[9px] hover:bg-slate-700 transition-colors flex items-center gap-1"
                                    onClick={(e) => { e.stopPropagation(); data.onExpand?.(data.id, 'features'); }}
                                >
                                    <span className="text-indigo-400">{data.features.length}</span>
                                    <span>features</span>
                                    <span className="text-indigo-400">▶</span>
                                </button>
                            )
                        )}
                    </div>
                </div>
            </div>
            
            {/* Side-Cars */}
            {isExpanded && expandType === 'questions' && hasQuestions && (
                <QuestionTray 
                    questions={data.questions}
                    nodeWidth={data.width}
                    onSubmit={(answers) => data.onSubmitQuestions?.(data.id, answers)}
                    onClose={() => data.onCollapse?.()}
                />
            )}
            
            {isExpanded && expandType === 'features' && hasFeatures && (
                <FeatureGrid 
                    features={data.features}
                    epicName={data.name}
                    nodeWidth={data.width}
                    onClose={() => data.onCollapse?.()}
                />
            )}
            
            <Handle type="source" position={Position.Bottom} className="!opacity-0" style={{left: '15%'}} />
        </div>
    );
}