/**
 * Block Component Registry
 * Maps schema IDs to React components for rendering RenderModel blocks
 */

import ParagraphBlock from './ParagraphBlock';
import StringListBlock from './StringListBlock';
import IndicatorBlock from './IndicatorBlock';
import OpenQuestionBlock from './OpenQuestionBlock';
import OpenQuestionsBlock from './OpenQuestionsBlock';
import RisksBlock from './RisksBlock';
import SummaryBlock from './SummaryBlock';
import StorySummaryBlock from './StorySummaryBlock';
import ArchComponentBlock from './ArchComponentBlock';
import WorkflowBlock from './WorkflowBlock';
import WorkflowBlockV2 from './WorkflowBlockV2';
import QualityAttributeBlock from './QualityAttributeBlock';
import DataModelBlock from './DataModelBlock';
import InterfaceBlock from './InterfaceBlock';
import GenericBlock from './GenericBlock';

// Discovery blocks
import UnknownsBlock from './UnknownsBlock';

// Intake compound blocks
import IntakeSummaryBlock from './IntakeSummaryBlock';
import IntakeProjectTypeBlock from './IntakeProjectTypeBlock';
import IntakeConstraintsBlock from './IntakeConstraintsBlock';
import IntakeOpenGapsBlock from './IntakeOpenGapsBlock';
import IntakeOutcomeBlock from './IntakeOutcomeBlock';

/**
 * Registry mapping schema IDs to React components
 */
const BLOCK_REGISTRY = {
    // Text/Content blocks
    'schema:ParagraphBlockV1': ParagraphBlock,
    'schema:StringListBlockV1': StringListBlock,
    'schema:IndicatorBlockV1': IndicatorBlock,

    // Question blocks
    'schema:OpenQuestionV1': OpenQuestionBlock,
    'schema:OpenQuestionsBlockV1': OpenQuestionsBlock,

    // Risk/Dependency blocks
    'schema:RisksBlockV1': RisksBlock,
    'schema:DependenciesBlockV1': RisksBlock, // Same visual treatment

    // Architecture blocks
    'schema:ArchComponentBlockV1': ArchComponentBlock,
    'schema:WorkflowBlockV1': WorkflowBlockV2, // V2 handles V1 data via auto-conversion
    'schema:WorkflowBlockV2': WorkflowBlockV2,
    'schema:QualityAttributeBlockV1': QualityAttributeBlock,
    'schema:DataModelBlockV1': DataModelBlock,
    'schema:InterfaceBlockV1': InterfaceBlock,

    // Summary blocks
    'schema:SummaryBlockV1': SummaryBlock,
    'schema:StorySummaryBlockV1': StorySummaryBlock,
    'schema:StoriesBlockV1': StringListBlock, // List of stories

    // Discovery blocks
    'schema:UnknownsBlockV1': UnknownsBlock,

    // Intake compound blocks
    'schema:IntakeSummaryBlockV1': IntakeSummaryBlock,
    'schema:IntakeProjectTypeBlockV1': IntakeProjectTypeBlock,
    'schema:IntakeConstraintsBlockV1': IntakeConstraintsBlock,
    'schema:IntakeOpenGapsBlockV1': IntakeOpenGapsBlock,
    'schema:IntakeOutcomeBlockV1': IntakeOutcomeBlock,
};

/**
 * Get the component for a block type
 */
export function getBlockComponent(schemaId) {
    return BLOCK_REGISTRY[schemaId] || GenericBlock;
}

/**
 * Render a single block
 */
export function renderBlock(block, index) {
    const Component = getBlockComponent(block.type);
    return <Component key={block.key || index} block={block} />;
}

export {
    ParagraphBlock,
    StringListBlock,
    IndicatorBlock,
    OpenQuestionBlock,
    OpenQuestionsBlock,
    RisksBlock,
    SummaryBlock,
    StorySummaryBlock,
    ArchComponentBlock,
    WorkflowBlock,
    WorkflowBlockV2,
    QualityAttributeBlock,
    DataModelBlock,
    InterfaceBlock,
    GenericBlock,
    UnknownsBlock,
    IntakeSummaryBlock,
    IntakeProjectTypeBlock,
    IntakeConstraintsBlock,
    IntakeOpenGapsBlock,
    IntakeOutcomeBlock,
};
