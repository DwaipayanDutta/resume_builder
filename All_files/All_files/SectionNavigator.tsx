import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useResumeStore } from "../store";

const LABELS: Record<string, string> = {
  summary: "Professional Summary",
  experience: "Work Experience",
  projects: "Projects",
  education: "Education",
  skills: "Skills",
  certifications: "Certifications",
};

function SortableSection({ id, active }: { id: string; active: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });
  const select = useResumeStore((s) => s.selectSection);

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
      className={`section-card ${active ? "active" : ""}`}
      onClick={() => select(id)}
    >
      <button className="drag-handle" {...attributes} {...listeners} aria-label="Drag to reorder">
        ⋮⋮
      </button>
      <span>{LABELS[id] ?? id}</span>
    </div>
  );
}

export function SectionNavigator() {
  const order = useResumeStore((s) => s.resume.section_order);
  const selected = useResumeStore((s) => s.selectedSection);
  const reorder = useResumeStore((s) => s.reorderSections);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={({ active, over }) => {
        if (!over || active.id === over.id) return;
        const from = order.indexOf(active.id as string);
        const to = order.indexOf(over.id as string);
        reorder(from, to);
      }}
    >
      <SortableContext items={order} strategy={verticalListSortingStrategy}>
        {order.map((id) => (
          <SortableSection key={id} id={id} active={selected === id} />
        ))}
      </SortableContext>
    </DndContext>
  );
}