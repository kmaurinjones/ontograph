# Mermaid Diagram Syntax Reference

Quick reference for generating valid Mermaid diagrams in documentation.

## Graph (Flowchart)

**Use for**: Architecture diagrams, process flows, component relationships

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

**Direction**:
- `TD` or `TB`: Top to bottom
- `BT`: Bottom to top
- `LR`: Left to right
- `RL`: Right to left

**Node Shapes**:
- `[Square]`: Rectangle
- `(Round)`: Rounded edges
- `{Diamond}`: Decision
- `((Circle))`: Circle
- `>Flag]`: Asymmetric shape
- `[(Database)]`: Cylinder

**Connections**:
- `-->`: Arrow
- `---`: Line
- `-.->`: Dotted arrow
- `==>`: Thick arrow
- `--text-->`: Labeled arrow

---

## Sequence Diagram

**Use for**: API request/response flows, async operations, inter-service communication

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB

    Client->>API: POST /endpoint
    activate API
    API->>DB: SELECT query
    activate DB
    DB-->>API: Results
    deactivate DB
    API-->>Client: JSON response
    deactivate API
```

**Syntax**:
- `participant Name`: Declare participant
- `A->>B`: Solid arrow (request)
- `A-->>B`: Dashed arrow (response)
- `activate/deactivate`: Show lifecycle
- `Note right of A: Text`: Add annotations

**Loops**:
```mermaid
sequenceDiagram
    loop Every 5s
        Client->>API: Heartbeat
        API-->>Client: OK
    end
```

---

## Entity Relationship Diagram

**Use for**: Database schemas, data models

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : ordered_in

    USER {
        int id PK
        string email UK
        string name
        date created_at
    }

    ORDER {
        int id PK
        int user_id FK
        date order_date
        decimal total
    }

    LINE_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
    }

    PRODUCT {
        int id PK
        string sku UK
        string name
        decimal price
    }
```

**Relationships**:
- `||--||`: One to one
- `||--o{`: One to many
- `}o--o{`: Many to many
- `||--|{`: One to one or more

**Cardinality symbols**:
- `||`: Exactly one
- `o|`: Zero or one
- `}o`: Zero or more
- `}|`: One or more

**Field annotations**:
- `PK`: Primary key
- `FK`: Foreign key
- `UK`: Unique key

---

## Class Diagram

**Use for**: OOP structures, component hierarchies

```mermaid
classDiagram
    Animal <|-- Dog
    Animal <|-- Cat
    Animal : +String name
    Animal : +int age
    Animal : +makeSound()

    class Dog {
        +String breed
        +bark()
    }

    class Cat {
        +int lives
        +meow()
    }
```

**Relationships**:
- `<|--`: Inheritance
- `*--`: Composition
- `o--`: Aggregation
- `-->`: Association
- `..>`: Dependency

**Visibility**:
- `+`: Public
- `-`: Private
- `#`: Protected
- `~`: Package

---

## State Diagram

**Use for**: UI state machines, workflow states

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Loading : start
    Loading --> Success : data received
    Loading --> Error : request failed
    Success --> [*]
    Error --> Idle : retry
```

---

## Gantt Chart

**Use for**: Project timelines (rare in code docs)

```mermaid
gantt
    title Development Timeline
    dateFormat  YYYY-MM-DD
    section Backend
    API Development    :a1, 2026-01-01, 30d
    Database Schema    :a2, after a1, 20d
    section Frontend
    Component Library  :b1, 2026-01-15, 25d
    Integration        :b2, after b1, 10d
```

---

## Pie Chart

**Use for**: Data distributions (rare in architecture docs)

```mermaid
pie
    title Violation Types Distribution
    "Omission of Risk" : 35
    "Misleading Efficacy" : 28
    "Inadequate Fair Balance" : 22
    "Other" : 15
```

---

## Tips for Code Documentation

1. **Choose the right diagram type**:
   - Architecture → Graph
   - API flows → Sequence
   - Database → ER Diagram
   - OOP → Class Diagram

2. **Keep it simple**: Limit to 10-15 nodes per diagram

3. **Use consistent naming**: Match code identifiers where possible

4. **Label relationships**: Add text to arrows for clarity

5. **Test syntax**: Mermaid errors break rendering—validate before saving

6. **Add context**: Include a text explanation before/after the diagram

---

## Validation

Before saving documentation, ensure:
- No syntax errors (balanced braces, proper keywords)
- All node IDs referenced in connections are declared
- Direction/layout makes sense for the content
- Diagram renders without errors in Mermaid Live Editor
