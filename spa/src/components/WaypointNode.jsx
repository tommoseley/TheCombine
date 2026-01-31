import { Handle, Position } from 'reactflow';

/**
 * Invisible junction node for manifold routing
 */
export default function WaypointNode() {
    return (
        <div style={{ width: 1, height: 1, background: 'transparent' }}>
            <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
            <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
        </div>
    );
}
