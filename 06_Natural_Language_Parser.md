# Natural Language Parser
**LangChain + local LLM to turn "fire-rated wall" into parameters**

Transform human-readable building specifications into structured IFC parameters and constraints. Uses LangChain framework with local LLM to enable offline, privacy-preserving natural language understanding.

## Overview
A natural language processing pipeline that converts plain-language building descriptions ("fire-rated wall", "accessible parking area", "high-efficiency HVAC") into precise, actionable IFC parameters for automated generation.

## Core Functions

### Intent Recognition
Identify what type of component the user is describing:
- **Entity Type**: Wall, door, window, column, beam, HVAC unit
- **Category**: Architectural, structural, MEP, sitework
- **Action**: Create, modify, find, validate

**Examples:**
- "Add a fire-rated wall to the corridor" → Create IfcWall with fire_rating property
- "Find all 2-hour walls on floors 2-4" → Query with fire_rating="2H" AND floor IN [2,3,4]
- "Upgrade this HVAC unit to high-efficiency" → Modify equipment with efficiency_rating="high"

### Property Extraction
Parse specifications and extract IFC properties:
- **Dimensions**: Height, width, thickness, area
- **Materials**: Concrete, steel, glass, gypsum
- **Performance**: Fire ratings, acoustic STC, thermal R-values
- **Codes**: Applicable standards and regulations
- **Constraints**: Accessibility, energy, structural requirements

**Examples:**
- "12-foot tall" → height: 3658.4 (in mm)
- "fire-rated for 2 hours" → fire_rating: "2H", fire_rating_duration: 120 (minutes)
- "meets Title-24" → compliance_tags: ["Title-24"]
- "ADA accessible" → accessibility_standard: "ADA 2010"

### Constraint Parsing
Extract and translate business rules and constraints:
- **Accessibility**: ADA compliance, mobility requirements
- **Energy**: Title-24, IECC zone requirements
- **Safety**: Fire codes, egress requirements
- **Structural**: Load capacity, seismic design category

### Ambiguity Resolution
Handle uncertain or incomplete specifications:
- Ask clarifying questions when needed
- Suggest standard options for vague input
- Provide confidence scores for uncertain extractions
- Log uncertain interpretations for feedback

## Architecture

### Processing Pipeline

```
User Input (text)
    ↓
Tokenization & Cleaning
    ↓
LangChain Processing
    ↓
Local LLM Inference
    ↓
Intent Classification
    ↓
Property Extraction
    ↓
Constraint Parsing
    ↓
Validation & Disambiguation
    ↓
IFC Parameters (JSON)
```

## Technical Implementation

### LangChain Integration

```python
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from ifc_parser import IFCParameterExtractor

# Initialize local LLM
llm = Ollama(model="mistral-7b-instruct")

# Create extraction chain
prompt = PromptTemplate(
    input_variables=["user_input", "schema"],
    template="""Extract IFC parameters from this description:
    
    Description: {user_input}
    
    Expected schema: {schema}
    
    Return JSON with extracted parameters."""
)

chain = LLMChain(llm=llm, prompt=prompt)

# Process user input
result = chain.run(
    user_input="Fire-rated wall, 2 hours, concrete with gypsum board",
    schema=wall_schema
)
```

### Local LLM Options
- **Mistral 7B**: Lightweight, good general understanding
- **Llama 2**: Larger model, better accuracy
- **Specialized Domain Model**: Fine-tuned on BIM terminology
- **Quantized Models**: Q4/Q5 for limited resources

### Fine-Tuning for Building Domain

```
Training Data Examples:
"fire-rated wall" → {entity_type: "IfcWall", fire_rating: "1H"}
"ADA accessible door" → {entity_type: "IfcDoor", width: 36, accessibility: "ADA2010"}
"Title-24 compliant HVAC" → {entity_type: "IfcEnergyConversionDevice", compliance: "Title24"}
...
```

## Example Processing

### Example 1: Fire-Rated Wall
```
INPUT:
"Add a 2-hour fire-rated wall between offices A and B, 12 feet tall"

PROCESSING:
- Intent: CREATE, Entity: IfcWall
- Properties: height=3658mm, fire_rating="2H"
- Constraints: Between offices, separate occupancies

OUTPUT JSON:
{
  "intent": "create",
  "entity_type": "IfcWall",
  "properties": {
    "height": 3658.4,
    "name": "Office Separation Wall",
    "fire_rating": "2H",
    "sound_transmission_class": 50
  },
  "constraints": {
    "placement": {
      "between": ["Office-A", "Office-B"]
    },
    "codes": ["IBC-703", "CBC-706"]
  },
  "confidence": 0.92
}
```

### Example 2: Accessible Parking
```
INPUT:
"Create an accessible parking space with accessible route and van-accessible, 
meet ADA standards"

OUTPUT JSON:
{
  "intent": "create",
  "entity_type": "IfcSite/ParkingArea",
  "properties": {
    "accessibility_standard": "ADA2010",
    "parking_space": {
      "width": 2438,
      "length": 5486,
      "type": "van_accessible"
    },
    "accessible_route": {
      "width": 1524,
      "slope": 0.048
    }
  },
  "constraints": {
    "codes": ["ADA2010 Chapter 5", "IBC 1106"]
  },
  "confidence": 0.88
}
```

## Deliverables
- [ ] LangChain integration framework
- [ ] Local LLM setup guide & container
- [ ] Intent classifier model
- [ ] Property extraction engine
- [ ] Constraint parser
- [ ] Ambiguity resolver
- [ ] Training data & fine-tuning scripts
- [ ] API endpoint for text input
- [ ] Confidence scoring system
- [ ] Feedback collection for model improvement

## Technical Stack
- **Framework**: LangChain (Python)
- **LLM**: Ollama (local deployment), Llama 2 or Mistral
- **NLP**: spaCy (additional parsing), regex patterns
- **Validation**: pydantic, jsonschema
- **APIs**: FastAPI for endpoint

## Configuration

```yaml
nlp_parser:
  model:
    provider: "ollama"
    name: "mistral-7b-instruct"
    context_length: 4096
  
  temperature: 0.3  # Lower = more deterministic
  top_p: 0.9
  
  cache:
    enable: true
    ttl: 3600
  
  validation:
    strict_mode: false
    confidence_threshold: 0.75
```

## Performance Metrics
- ✓ Inference latency <2 seconds per input
- ✓ 85%+ accuracy on property extraction
- ✓ 25+ supported entity types
- ✓ <100MB memory footprint (quantized)
- ✓ Offline operation (no API dependencies)

## Privacy & Security
- All processing happens locally
- No data sent to external APIs
- Support for encrypted model files
- Audit logs for all interpretations

## Testing Strategy

```bash
# Unit tests for each component
pytest tests/unit/nlp/

# Integration tests
pytest tests/integration/nlp_to_ifc/

# Benchmark inference speed
pytest tests/performance/inference_speed.py

# Accuracy benchmarks on test set
pytest tests/validation/extraction_accuracy.py
```

## Usage Examples

### Python API
```python
from ifc_nlp import TextToIFC

parser = TextToIFC()

# Single input
result = parser.parse("fire-rated wall, 2 hours")

# Batch processing
results = parser.parse_batch([
    "fire-rated wall, 2 hours",
    "ADA accessible door",
    "high-efficiency HVAC"
])

# With context
context = {
    "project_type": "office_building",
    "climate_zone": "4A",
    "jurisdiction": "California"
}
result = parser.parse(text, context=context)
```

### REST API
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "fire-rated wall 2 hours"}'

Response:
{
  "intent": "create",
  "entity_type": "IfcWall",
  "properties": {...},
  "confidence": 0.92
}
```

## Continuous Improvement
- Collect user feedback on parsing accuracy
- Track misinterpretations and add to training data
- Periodically fine-tune on domain-specific examples
- Share improvements across team instances
- Monitor performance on new building types

## Future Enhancements
- Multi-language support
- Context-aware parsing (project history, team preferences)
- Voice/speech input support
- Conversation-based refinement ("Actually, make it 3 hours")
- Integration with email/chat for batch processing
