import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useResumeStore } from "../store";

const LABELS: Record<string, { label: string; icon: string }> = {
  contact: { label: "Contact Info", icon: "👤" },
  summary: { label: "Professional Summary", icon: "📄" },
  experience: { label: "Work Experience", icon: "💼" },
  projects: { label: "Projects", icon: "🚀" },
  education: { label: "Education", icon: "🎓" },
  skills: { label: "Skills", icon: "⚡" },
  certifications: { label: "Certifications", icon: "📜" },
};

function SortableSection({ id, active }: { id: string; active: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });
  const select = useResumeStore((s) => s.selectSection);
  const info = LABELS[id] ?? { label: id, icon: "📌" };

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
      className={`section-card ${active ? "active" : ""}`}
      onClick={() => select(id)}
    >
      <button
        type="button"
        className="drag-handle"
        {...attributes}
        {...listeners}
        aria-label={`Drag to reorder ${info.label}`}
      >
        ⋮⋮
      </button>
      <span className="section-icon">{info.icon}</span>
      <span className="section-title">{info.label}</span>
    </div>
  );
}

export function SectionNavigator() {
  const order = useResumeStore((s) => s.resume?.section_order ?? []);
  const selected = useResumeStore((s) => s.selectedSection);
  const select = useResumeStore((s) => s.selectSection);
  const reorder = useResumeStore((s) => s.reorderSections);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  return (
    <div className="section-navigator">
      <div className="nav-header">
        <span className="nav-heading">SECTIONS</span>
      </div>

      <div
        className={`section-card fixed-section ${
          selected === "contact" ? "active" : ""
        }`}
        onClick={() => select("contact")}
      >
        <span className="section-icon">👤</span>
        <span className="section-title">Contact Info</span>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={({ active, over }) => {
          if (!over || active.id === over.id) return;
          const from = order.indexOf(active.id as string);
          const to = order.indexOf(over.id as string);
          if (from !== -1 && to !== -1) {
            reorder(from, to);
          }
        }}
      >
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          {order.map((id) => (
            <SortableSection key={id} id={id} active={selected === id} />
          ))}
        </SortableContext>
      </DndContext>
    </div>
  );
}
