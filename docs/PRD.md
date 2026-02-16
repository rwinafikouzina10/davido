# TruckParking Optimizer — Product Requirements Document

**Version:** 1.0  
**Date:** 2026-02-16  
**Status:** MVP Development  

---

## 1. Product Overview

### 1.1 Purpose
A web-based tool for optimizing truck parking lot layouts, ensuring regulatory compliance, and maximizing revenue potential for the Havenweg 4 facility in Echt, Netherlands.

### 1.2 Target Users
- Parking facility managers
- Operations planners
- Facility owners (Green Caravan)

### 1.3 Key Objectives
1. Visualize and edit parking lot layouts interactively
2. Validate compliance with Dutch/EU parking regulations
3. Calculate revenue projections under different scenarios
4. Enable scenario comparison for decision-making

---

## 2. User Stories

### Layout Editor
- **US-1:** As a planner, I want to see the parking lot layout on a visual canvas so I can understand the current configuration.
- **US-2:** As a planner, I want to add new parking spaces with specific types so I can experiment with layouts.
- **US-3:** As a planner, I want to move and resize parking spaces so I can optimize space utilization.
- **US-4:** As a planner, I want to delete parking spaces so I can try different configurations.

### Compliance
- **US-5:** As a planner, I want real-time compliance feedback so I know when my layout violates regulations.
- **US-6:** As a planner, I want to see specific violations highlighted so I can fix them.

### Revenue
- **US-7:** As a manager, I want to see revenue projections based on occupancy so I can plan financially.
- **US-8:** As a manager, I want to compare revenue across scenarios so I can choose the best layout.

### Data Management
- **US-9:** As a user, I want to save my layouts so I can continue work later.
- **US-10:** As a user, I want to export layouts as JSON so I can share or backup my work.

---

## 3. Functional Requirements

### 3.1 Layout Visualizer

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Display parking lot canvas with configurable dimensions | P0 |
| FR-1.2 | Support background image upload (blueprints) | P1 |
| FR-1.3 | Show parking spaces as colored rectangles by type | P0 |
| FR-1.4 | Display space numbers/labels | P0 |
| FR-1.5 | Show lot boundary outline | P0 |
| FR-1.6 | Zoom and pan support | P2 |

### 3.2 Parking Space Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Add parking space via form (position, type, dimensions) | P0 |
| FR-2.2 | Edit existing parking space properties | P0 |
| FR-2.3 | Delete parking space | P0 |
| FR-2.4 | Support all space types (truck, tractor, trailer, EV, van) | P0 |
| FR-2.5 | Bulk operations (select multiple) | P2 |
| FR-2.6 | Space rotation support | P1 |

### 3.3 Compliance Checker

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Validate minimum space dimensions | P0 |
| FR-3.2 | Check minimum spacing between vehicles (1m) | P0 |
| FR-3.3 | Validate lane widths | P1 |
| FR-3.4 | Check fire access requirements | P1 |
| FR-3.5 | Detect overlapping spaces | P0 |
| FR-3.6 | Display compliance status (pass/fail per check) | P0 |
| FR-3.7 | Show violations on canvas | P1 |

### 3.4 Revenue Calculator

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Calculate revenue based on space count by type | P0 |
| FR-4.2 | Configurable occupancy rate input | P0 |
| FR-4.3 | Show daily/weekly/monthly/annual projections | P0 |
| FR-4.4 | Compare to revenue target (€200k/year) | P0 |
| FR-4.5 | Revenue breakdown by space type | P1 |

### 3.5 Scenario Planning

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Save current layout as named scenario | P0 |
| FR-5.2 | Load and switch between scenarios | P0 |
| FR-5.3 | Compare scenarios side-by-side (metrics) | P1 |
| FR-5.4 | Duplicate scenario for variations | P1 |

### 3.6 Data Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | Export layout to JSON | P0 |
| FR-6.2 | Import layout from JSON | P0 |
| FR-6.3 | Auto-save to browser/session | P1 |
| FR-6.4 | Download as image | P2 |

---

## 4. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Page load time | < 3 seconds |
| NFR-2 | Compliance check latency | < 500ms |
| NFR-3 | Browser support | Chrome, Firefox, Safari |
| NFR-4 | Mobile responsive | Basic support |
| NFR-5 | Data persistence | Session + file export |

---

## 5. Technical Architecture

### 5.1 Stack
- **Frontend:** Streamlit (Python)
- **Visualization:** Plotly
- **Backend Logic:** Python (pandas)
- **Storage:** JSON files

### 5.2 Data Model

```python
ParkingSpace:
  id: str
  x: float  # meters
  y: float  # meters
  length: float  # meters
  width: float  # meters
  rotation: float  # degrees
  type: enum[truck, tractor, trailer, ev, van]
  label: str

Layout:
  name: str
  created: datetime
  lot_width: float
  lot_length: float
  spaces: list[ParkingSpace]
  
Scenario:
  name: str
  layout: Layout
  occupancy_rate: float
  notes: str
```

---

## 6. Success Metrics

| Metric | Target |
|--------|--------|
| Layout creation time | < 15 minutes |
| Compliance check accuracy | 100% for implemented rules |
| User can compare 3+ scenarios | Yes |
| Revenue projection accuracy | ±5% vs manual calculation |

---

## 7. Out of Scope (Future)

- Real-time occupancy tracking
- Booking system integration
- Multi-site support
- EV charging infrastructure planning
- Demand forecasting
- Automated optimization algorithms

---

## 8. Milestones

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| M1 | Day 1 | Project setup, basic canvas |
| M2 | Day 2 | Space management, compliance |
| M3 | Day 3 | Revenue calculator, scenarios |
| M4 | Day 4 | Polish, testing, demo ready |
