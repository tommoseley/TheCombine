// components/nodes/StationDots.jsx
// Mini progress tracker showing station states

export default function StationDots({ stations }) {
    if (!stations?.length) return null;
    
    return (
        <div className="flex items-center gap-0.5 mt-2">
            {stations.map((s, i) => {
                const dotColor = s.state === 'complete' ? 'bg-emerald-500' : 
                                 s.state === 'active' ? 'bg-indigo-500' : 'bg-slate-600';
                const lineColor = s.state === 'complete' ? 'bg-emerald-500' : 'bg-slate-600';
                
                return (
                    <React.Fragment key={s.id}>
                        {i > 0 && <div className={'w-4 h-0.5 ' + lineColor} />}
                        <div className="flex flex-col items-center">
                            <div className={'w-3 h-3 rounded-full ' + dotColor + (s.state === 'active' ? ' station-active' : '')} />
                            <span className={'text-[7px] mt-0.5 ' + (s.state === 'active' ? 'text-indigo-400 font-medium' : 'text-slate-500')}>
                                {s.label}
                            </span>
                        </div>
                    </React.Fragment>
                );
            })}
        </div>
    );
}