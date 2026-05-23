from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.chapter_character import ChapterCharacter
from app.models.chapter_clue import ChapterClue
from app.models.chapter_setting import ChapterSetting
from app.models.character import Character
from app.models.clue import Clue
from app.models.graph_node import GraphNode
from app.models.outline_item import OutlineItem
from app.models.project import Project
from app.models.setting_item import SettingItem
from app.models.timeline_event import TimelineEvent
from app.schemas.creative_reminder import CreativeReminderRead

_SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}

_RULE_META: dict[str, dict[str, str]] = {
    "important_clue_unresolved": {
        "reason": "重要伏笔从埋设后经过较多章节仍未回收，读者可能遗忘或认为线索断裂。",
        "suggestion": "检查该伏笔是否仍需要保留；如需要，请规划回收章节或在近期章节补一次提示；如不需要，请将伏笔状态调整为废弃或降低重要性。",
    },
    "important_character_absent": {
        "reason": "重要人物长时间未出场或未被章节绑定，可能削弱人物存在感。",
        "suggestion": "考虑安排该人物出场、被其他角色提及，或在人物资料中下调重要性。",
    },
    "outline_not_done_for_written_chapter": {
        "reason": "章节已有正文，但关联大纲仍处于未完成状态，可能导致进度记录不准确。",
        "suggestion": "确认正文是否已覆盖该大纲目标；如果已完成，请更新大纲状态；如果未完成，请补充遗漏情节。",
    },
    "timeline_event_missing_chapter": {
        "reason": "重要时间线事件没有绑定章节，后续查找和一致性检查会变弱。",
        "suggestion": "为该事件绑定发生章节；如果它只是背景事件，请在备注中说明并降低重要性。",
    },
    "graph_node_broken_binding": {
        "reason": "关系图节点绑定的资料不存在或已删除，图谱可能显示失效信息。",
        "suggestion": "重新绑定到有效资料，或将节点改为自定义节点并更新说明。",
    },
    "clue_payoff_without_setup": {
        "reason": "伏笔有回收记录但缺少埋设记录，读者可能感到回收突兀。",
        "suggestion": "补充埋设章节或设置埋设关系；如果回收本身不需要前置伏笔，请调整伏笔状态和说明。",
    },
    "setting_used_but_draft": {
        "reason": "章节已使用草稿设定，可能导致正文引用未定稿内容。",
        "suggestion": "确认该设定是否已经稳定；如果稳定，请将设定状态改为正式；如果仍在试验，请在章节备注中标记风险。",
    },
}



class CreativeReminderProjectNotFoundError(Exception):
    pass


class CreativeReminderService:
    def __init__(self, db: Session):
        self.db = db

    def list_project_reminders(
        self,
        project_id: str,
        *,
        scope: str = "project",
        chapter_id: str | None = None,
        severity: str | None = None,
        reminder_type: str | None = None,
    ) -> list[CreativeReminderRead]:
        project = self.db.scalar(
            select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        if project is None:
            raise CreativeReminderProjectNotFoundError

        chapters = list(
            self.db.scalars(
                select(Chapter)
                .where(Chapter.project_id == project_id, Chapter.deleted_at.is_(None))
                .order_by(Chapter.volume_id.asc(), Chapter.order_index.asc(), Chapter.created_at.asc())
            ).all()
        )
        chapter_index = {chapter.id: index for index, chapter in enumerate(chapters)}
        scope_chapter_index = chapter_index.get(chapter_id or "", len(chapters) - 1)

        reminders: list[CreativeReminderRead] = []
        reminders.extend(self._important_clue_unresolved(project_id, chapter_index, scope_chapter_index))
        reminders.extend(self._important_character_absent(project_id, chapter_index, scope_chapter_index))
        reminders.extend(self._outline_not_done_for_written_chapter(project_id))
        reminders.extend(self._timeline_event_missing_chapter(project_id))
        reminders.extend(self._graph_node_broken_binding(project_id))
        reminders.extend(self._clue_payoff_without_setup(project_id))
        reminders.extend(self._setting_used_but_draft(project_id))

        if scope == "chapter" and chapter_id:
            reminders = [
                item for item in reminders
                if item.chapter_id in (None, chapter_id) or item.target_id == chapter_id
            ]
        if chapter_id:
            chapter_related_target_ids = self._chapter_related_target_ids(chapter_id)
            reminders = [
                item for item in reminders
                if item.chapter_id in (None, chapter_id)
                or item.target_id in chapter_related_target_ids
                or item.target_type in ("timeline_event", "graph_node")
            ]
        if severity:
            reminders = [item for item in reminders if item.severity == severity]
        if reminder_type:
            reminders = [item for item in reminders if item.type == reminder_type]

        return self._sort_reminders(reminders)

    def _important_clue_unresolved(
        self,
        project_id: str,
        chapter_index: dict[str, int],
        current_index: int,
    ) -> list[CreativeReminderRead]:
        reminders: list[CreativeReminderRead] = []
        clues = list(
            self.db.scalars(
                select(Clue).where(
                    Clue.project_id == project_id,
                    Clue.deleted_at.is_(None),
                    Clue.importance.in_(["high", "critical"]),
                    Clue.status.in_(["planted", "developing"]),
                )
            ).all()
        )
        for clue in clues:
            setup_chapter_id = clue.setup_chapter_id or self._first_clue_relation_chapter(clue.id, "setup")
            if not setup_chapter_id or clue.payoff_chapter_id:
                continue
            distance = current_index - chapter_index.get(setup_chapter_id, current_index)
            if distance <= 20:
                continue
            severity = "critical" if clue.importance == "critical" else "warning"
            reminders.append(self._item(
                project_id,
                setup_chapter_id,
                "important_clue_unresolved",
                severity,
                "重要伏笔长期未回收",
                f"伏笔“{clue.title}”已推进 {distance} 章以上，尚未回收。",
                "clue",
                clue.id,
                "查看伏笔",
                scope_label="全书",
                context_summary=f"伏笔“{clue.title}”·距埋设 {distance} 章",
            ))
        return reminders

    def _important_character_absent(
        self,
        project_id: str,
        chapter_index: dict[str, int],
        current_index: int,
    ) -> list[CreativeReminderRead]:
        reminders: list[CreativeReminderRead] = []
        characters = list(
            self.db.scalars(
                select(Character).where(
                    Character.project_id == project_id,
                    Character.deleted_at.is_(None),
                    Character.importance.in_(["high", "critical"]),
                )
            ).all()
        )
        relations = list(
            self.db.scalars(
                select(ChapterCharacter).where(ChapterCharacter.project_id == project_id)
            ).all()
        )
        by_character: dict[str, list[ChapterCharacter]] = {}
        for relation in relations:
            by_character.setdefault(relation.character_id, []).append(relation)

        for character in characters:
            last_index = -1
            last_chapter_id: str | None = None
            for relation in by_character.get(character.id, []):
                index = chapter_index.get(relation.chapter_id)
                if index is not None and index > last_index:
                    last_index = index
                    last_chapter_id = relation.chapter_id
            if last_index < 0:
                continue
            distance = current_index - last_index
            if distance <= 20:
                continue
            reminders.append(self._item(
                project_id,
                last_chapter_id,
                "important_character_absent",
                "warning" if character.importance == "critical" else "info",
                "重要人物长期未出场",
                f"人物“{character.name}”已经 {distance} 章未出场或被提及。",
                "character",
                character.id,
                "查看人物",
                scope_label="全书",
                context_summary=f"人物“{character.name}”·已缺席 {distance} 章",
            ))
        return reminders

    def _outline_not_done_for_written_chapter(self, project_id: str) -> list[CreativeReminderRead]:
        rows = self.db.execute(
            select(OutlineItem, Chapter)
            .join(Chapter, OutlineItem.chapter_id == Chapter.id)
            .where(
                OutlineItem.project_id == project_id,
                OutlineItem.deleted_at.is_(None),
                OutlineItem.status.in_(["planned", "writing"]),
                Chapter.deleted_at.is_(None),
                Chapter.content != "",
            )
        ).all()
        return [
            self._item(
                project_id,
                chapter.id,
                "outline_not_done_for_written_chapter",
                "info",
                "已写章节仍有未完成细纲",
                f"章节“{chapter.title}”已有正文，但细纲“{outline.title}”仍未完成。",
                "outline",
                outline.id,
                "查看大纲",
                scope_label="关联章节",
                context_summary=f"章节“{chapter.title}”·细纲“{outline.title}”",
            )
            for outline, chapter in rows
        ]

    def _timeline_event_missing_chapter(self, project_id: str) -> list[CreativeReminderRead]:
        events = list(
            self.db.scalars(
                select(TimelineEvent).where(
                    TimelineEvent.project_id == project_id,
                    TimelineEvent.deleted_at.is_(None),
                    TimelineEvent.importance.in_(["high", "critical"]),
                    TimelineEvent.chapter_id.is_(None),
                )
            ).all()
        )
        return [
            self._item(
                project_id,
                None,
                "timeline_event_missing_chapter",
                "warning",
                "重要时间轴事件未绑定章节",
                f"事件“{event.title}”尚未绑定章节。",
                "timeline_event",
                event.id,
                "查看时间轴",
                scope_label="全书",
                context_summary=f"事件“{event.title}”",
            )
            for event in events
        ]

    def _graph_node_broken_binding(self, project_id: str) -> list[CreativeReminderRead]:
        nodes = list(
            self.db.scalars(
                select(GraphNode).where(
                    GraphNode.project_id == project_id,
                    GraphNode.deleted_at.is_(None),
                    GraphNode.bound_type.is_not(None),
                    GraphNode.bound_id.is_not(None),
                )
            ).all()
        )
        reminders: list[CreativeReminderRead] = []
        for node in nodes:
            if node.bound_type == "custom" or not node.bound_id:
                continue
            if self._bound_exists(project_id, node.bound_type, node.bound_id):
                continue
            reminders.append(self._item(
                project_id,
                None,
                "graph_node_broken_binding",
                "warning",
                "关系图节点绑定已失效",
                f"节点“{node.title}”绑定的资料不存在或已删除。",
                "graph_node",
                node.id,
                "查看关系图",
                scope_label="跨资料",
                context_summary=f"节点“{node.title}”",
            ))
        return reminders

    def _clue_payoff_without_setup(self, project_id: str) -> list[CreativeReminderRead]:
        payoff_relations = list(
            self.db.scalars(
                select(ChapterClue).where(
                    ChapterClue.project_id == project_id,
                    ChapterClue.relation_type == "payoff",
                )
            ).all()
        )
        reminders: list[CreativeReminderRead] = []
        for relation in payoff_relations:
            clue = self.db.scalar(
                select(Clue).where(
                    Clue.id == relation.clue_id,
                    Clue.deleted_at.is_(None),
                )
            )
            if clue is None or clue.setup_chapter_id:
                continue
            has_setup = self.db.scalar(
                select(ChapterClue).where(
                    ChapterClue.clue_id == relation.clue_id,
                    ChapterClue.relation_type == "setup",
                )
            )
            if has_setup is not None:
                continue
            reminders.append(self._item(
                project_id,
                relation.chapter_id,
                "clue_payoff_without_setup",
                "warning",
                "伏笔回收缺少埋设记录",
                f"伏笔“{clue.title}”有回收关系，但没有埋设章节或埋设关系。",
                "clue",
                clue.id,
                "查看伏笔",
                scope_label="全书",
                context_summary=f"伏笔“{clue.title}”",
            ))
        return reminders

    def _setting_used_but_draft(self, project_id: str) -> list[CreativeReminderRead]:
        rows = self.db.execute(
            select(ChapterSetting, SettingItem)
            .join(SettingItem, ChapterSetting.setting_item_id == SettingItem.id)
            .where(
                ChapterSetting.project_id == project_id,
                SettingItem.deleted_at.is_(None),
                SettingItem.canon_status == "draft",
            )
        ).all()
        return [
            self._item(
                project_id,
                relation.chapter_id,
                "setting_used_but_draft",
                "info",
                "本章使用了草稿设定",
                f"设定“{setting.title}”仍是草稿状态。",
                "setting",
                setting.id,
                "查看设定",
                scope_label="关联章节",
                context_summary=f"设定“{setting.title}”",
            )
            for relation, setting in rows
        ]

    def _chapter_related_target_ids(self, chapter_id: str) -> set[str]:
        ids = {chapter_id}
        for relation in self.db.scalars(select(ChapterCharacter).where(ChapterCharacter.chapter_id == chapter_id)).all():
            ids.add(relation.character_id)
        for relation in self.db.scalars(select(ChapterClue).where(ChapterClue.chapter_id == chapter_id)).all():
            ids.add(relation.clue_id)
        for relation in self.db.scalars(select(ChapterSetting).where(ChapterSetting.chapter_id == chapter_id)).all():
            ids.add(relation.setting_item_id)
        for outline in self.db.scalars(select(OutlineItem).where(OutlineItem.chapter_id == chapter_id)).all():
            ids.add(outline.id)
        for event in self.db.scalars(select(TimelineEvent).where(TimelineEvent.chapter_id == chapter_id)).all():
            ids.add(event.id)
        return ids

    def _first_clue_relation_chapter(self, clue_id: str, relation_type: str) -> str | None:
        relation = self.db.scalar(
            select(ChapterClue)
            .where(ChapterClue.clue_id == clue_id, ChapterClue.relation_type == relation_type)
            .order_by(ChapterClue.created_at.asc())
        )
        return relation.chapter_id if relation else None

    def _bound_exists(self, project_id: str, bound_type: str, bound_id: str) -> bool:
        model_map = {
            "character": Character,
            "setting": SettingItem,
            "clue": Clue,
            "timeline_event": TimelineEvent,
        }
        model = model_map.get(bound_type)
        if model is None:
            return False
        item = self.db.scalar(
            select(model).where(
                model.id == bound_id,
                model.project_id == project_id,
                model.deleted_at.is_(None),
            )
        )
        return item is not None

    def _item(
        self,
        project_id: str,
        chapter_id: str | None,
        reminder_type: str,
        severity: str,
        title: str,
        message: str,
        target_type: str,
        target_id: str,
        action_label: str,
        scope_label: str,
        context_summary: str | None = None,
    ) -> CreativeReminderRead:
        meta = _RULE_META.get(reminder_type, {"reason": "", "suggestion": ""})
        return CreativeReminderRead(
            id=f"{reminder_type}:{target_type}:{target_id}:{chapter_id or 'project'}",
            project_id=project_id,
            chapter_id=chapter_id,
            type=reminder_type,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            title=title,
            message=message,
            reason=meta["reason"],
            suggestion=meta["suggestion"],
            scope_label=scope_label,
            context_summary=context_summary,
            target_type=target_type,  # type: ignore[arg-type]
            target_id=target_id,
            action_label=action_label,
            created_from="rule",
        )

    @staticmethod
    def _sort_reminders(reminders: list[CreativeReminderRead]) -> list[CreativeReminderRead]:
        return sorted(
            reminders,
            key=lambda item: (
                _SEVERITY_RANK.get(item.severity, 99),
                0 if item.chapter_id is not None else 1,
            ),
        )
