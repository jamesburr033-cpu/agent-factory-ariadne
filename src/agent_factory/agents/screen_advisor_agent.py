from __future__ import annotations

from ..schemas import RecommendedAction, ScreenObservation, UserTask


class ScreenAdvisorAgent:
    """Mocked v0.1 screen analysis agent.

    Future versions can connect to screenshot OCR/computer-use tools.
    This version only infers context from task text and optional screenshot path.
    """

    def analyze(self, task: UserTask) -> tuple[ScreenObservation, list[RecommendedAction]]:
        text = task.text.lower()

        if "servicenow" in text or "snow" in text or "ticket" in text:
            observation = ScreenObservation(
                screen_type="ServiceNow ticket form, inferred",
                app_name="ServiceNow",
                visible_fields=["Short description", "Description", "Assignment group", "Work notes"],
                notes=["Mock inference only. No real screen control was performed."],
                confidence="medium",
            )
            actions = [
                RecommendedAction(
                    action_type="suggest_values",
                    description="Suggest draft ticket field values from task context.",
                    app_name="ServiceNow",
                    risk_level="low",
                ),
                RecommendedAction(
                    action_type="fill_field",
                    description="Fill Short description with a concise draft value, only in assisted/demo mode.",
                    app_name="ServiceNow",
                    field_name="Short description",
                    value=self._short_description(task.text),
                    risk_level="medium",
                ),
                RecommendedAction(
                    action_type="fill_field",
                    description="Fill Work notes with a safe draft summary, only in assisted/demo mode.",
                    app_name="ServiceNow",
                    field_name="Work notes",
                    value="Draft work notes based on reviewed source context. Stop before save/submit.",
                    risk_level="medium",
                ),
                RecommendedAction(
                    action_type="submit_form",
                    description="Submit the ticket form. This must require approval and should not run in v0.1.",
                    app_name="ServiceNow",
                    risk_level="high",
                    reversible=False,
                ),
            ]
            return observation, actions

        if "epic" in text or "hyperspace" in text:
            observation = ScreenObservation(
                screen_type="Epic build/advisory context, inferred",
                app_name="Browser",
                visible_fields=[],
                notes=[
                    "Epic production automation is blocked by default.",
                    "Use advisory mode, sandbox context, and approved documentation only.",
                ],
                confidence="medium",
            )
            actions = [
                RecommendedAction(
                    action_type="suggest_values",
                    description="Suggest build-analysis checklist and likely missing inputs.",
                    app_name="Browser",
                    risk_level="low",
                )
            ]
            return observation, actions

        observation = ScreenObservation(
            screen_type="Unknown or general screen, inferred",
            app_name="Browser",
            visible_fields=[],
            notes=["No screenshot parsing is active in v0.1."],
            confidence="low",
        )
        actions = [
            RecommendedAction(
                action_type="suggest_values",
                description="Suggest next safe step only. Do not click or type.",
                app_name="Browser",
                risk_level="low",
            )
        ]
        return observation, actions

    def _short_description(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        if len(cleaned) <= 90:
            return cleaned
        return cleaned[:87].rstrip() + "..."
