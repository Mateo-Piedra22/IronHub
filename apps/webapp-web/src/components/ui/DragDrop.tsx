'use client';

import React from 'react';
import {
    DndContext,
    DragEndEvent,
    DragOverEvent,
    DragStartEvent,
    DragOverlay,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    UniqueIdentifier,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
export interface SortableItem {
    id: string | number;
    [key: string]: unknown;
}

// Sortable Item Component
interface SortableItemProps {
    item: SortableItem;
    children: React.ReactNode;
    disabled?: boolean;
}

export function SortableItemWrapper({ item, children, disabled }: SortableItemProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: item.id, disabled });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div ref={setNodeRef} style={style} className="relative group">
            <div
                {...attributes}
                {...listeners}
                className={cn(
                    'absolute left-0 top-1/2 -translate-y-1/2 -ml-2 p-1 rounded cursor-grab',
                    'text-slate-600 hover:text-slate-400 transition-colors',
                    'opacity-0 group-hover:opacity-100',
                    disabled && 'hidden'
                )}
            >
                <GripVertical className="w-4 h-4" />
            </div>
            {children}
        </div>
    );
}

// Sortable List Container
interface SortableListProps<T extends SortableItem> {
    items: T[];
    onReorder: (items: T[]) => void;
    renderItem: (item: T, index: number) => React.ReactNode;
    disabled?: boolean;
}

export function SortableList<T extends SortableItem>({
    items,
    onReorder,
    renderItem,
    disabled,
}: SortableListProps<T>) {
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;

        if (over && active.id !== over.id) {
            const oldIndex = items.findIndex((item) => item.id === active.id);
            const newIndex = items.findIndex((item) => item.id === over.id);
            onReorder(arrayMove(items, oldIndex, newIndex));
        }
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
        >
            <SortableContext
                items={items.map((i) => i.id)}
                strategy={verticalListSortingStrategy}
            >
                <div className="space-y-2">
                    {items.map((item, index) => (
                        <SortableItemWrapper key={item.id} item={item} disabled={disabled}>
                            {renderItem(item, index)}
                        </SortableItemWrapper>
                    ))}
                </div>
            </SortableContext>
        </DndContext>
    );
}

// Kanban-style multi-column drag-drop
interface KanbanColumn<T extends SortableItem> {
    id: string | number;
    title: string;
    items: T[];
}

interface KanbanBoardProps<T extends SortableItem> {
    columns: KanbanColumn<T>[];
    onMove: (itemId: UniqueIdentifier, fromColumn: UniqueIdentifier, toColumn: UniqueIdentifier, newIndex: number) => void;
    onReorder: (columnId: UniqueIdentifier, items: T[]) => void;
    renderItem: (item: T, columnId: UniqueIdentifier) => React.ReactNode;
    renderColumn?: (column: KanbanColumn<T>, children: React.ReactNode) => React.ReactNode;
}

export function KanbanBoard<T extends SortableItem>({
    columns,
    onMove,
    onReorder,
    renderItem,
    renderColumn,
}: KanbanBoardProps<T>) {
    const [activeItem, setActiveItem] = React.useState<T | null>(null);
    const [activeColumn, setActiveColumn] = React.useState<UniqueIdentifier | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Find which column an item belongs to
    const findColumn = (id: UniqueIdentifier): KanbanColumn<T> | undefined => {
        for (const column of columns) {
            if (column.items.some((item) => item.id === id)) {
                return column;
            }
        }
        return undefined;
    };

    const handleDragStart = (event: DragStartEvent) => {
        const column = findColumn(event.active.id);
        if (column) {
            const item = column.items.find((i) => i.id === event.active.id);
            setActiveItem(item || null);
            setActiveColumn(column.id);
        }
    };

    const handleDragOver = (event: DragOverEvent) => {
        const { active, over } = event;
        if (!over) return;

        const activeCol = findColumn(active.id);

        // Check if hovering over a column header
        const overColumn = columns.find((col) => col.id === over.id);
        if (overColumn && activeCol && activeCol.id !== overColumn.id) {
            // Move to empty column or append to end
            onMove(active.id, activeCol.id, overColumn.id, overColumn.items.length);
            return;
        }

        const overCol = findColumn(over.id);

        if (!activeCol || !overCol) return;

        if (activeCol.id !== overCol.id) {
            const overIndex = overCol.items.findIndex((i) => i.id === over.id);
            onMove(active.id, activeCol.id, overCol.id, overIndex);
        }
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;

        if (over) {
            const activeCol = findColumn(active.id);
            const overCol = findColumn(over.id);

            if (activeCol && overCol && activeCol.id === overCol.id && active.id !== over.id) {
                const oldIndex = activeCol.items.findIndex((i) => i.id === active.id);
                const newIndex = activeCol.items.findIndex((i) => i.id === over.id);
                onReorder(activeCol.id, arrayMove(activeCol.items, oldIndex, newIndex));
            }
        }

        setActiveItem(null);
        setActiveColumn(null);
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
        >
            <div className="flex gap-4 overflow-x-auto pb-4">
                {columns.map((column) => (
                    <div key={column.id} className="flex-shrink-0 w-72">
                        <SortableContext
                            items={column.items.map((i) => i.id)}
                            strategy={verticalListSortingStrategy}
                            id={String(column.id)}
                        >
                            {renderColumn ? (
                                renderColumn(
                                    column,
                                    <div className="space-y-2 min-h-[100px]">
                                        {column.items.map((item) => (
                                            <SortableItemWrapper key={item.id} item={item}>
                                                {renderItem(item, column.id)}
                                            </SortableItemWrapper>
                                        ))}
                                    </div>
                                )
                            ) : (
                                <div className="card">
                                    <div className="p-3 border-b border-slate-800">
                                        <h3 className="font-medium text-white">{column.title}</h3>
                                    </div>
                                    <div className="p-3 space-y-2 min-h-[100px]">
                                        {column.items.map((item) => (
                                            <SortableItemWrapper key={item.id} item={item}>
                                                {renderItem(item, column.id)}
                                            </SortableItemWrapper>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </SortableContext>
                    </div>
                ))}
            </div>
            <DragOverlay>
                {activeItem && activeColumn && (
                    <div className="opacity-80">
                        {renderItem(activeItem, activeColumn)}
                    </div>
                )}
            </DragOverlay>
        </DndContext>
    );
}

export { arrayMove };

