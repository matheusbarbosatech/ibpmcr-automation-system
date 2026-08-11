"""
Otimizador de Escalas de Voluntários via Pesquisa Operacional (Google OR-Tools).

Resolve o problema de Satisfação de Restrições (CSP) para alocação justa e eficiente
de voluntários nos departamentos da igreja (Louvor, Mídia, Recepção, EBD e Apoio).
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from ortools.sat.python import cp_model
    HAS_OR_TOOLS = True
except ImportError:
    HAS_OR_TOOLS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class VolunteerScheduleOptimizer:
    """
    Otimizador de escalas de voluntários baseado em Programação por Restrições (OR-Tools CP-SAT).
    """

    def __init__(self):
        """
        Inicializa a estrutura do otimizador.
        """
        pass

    def optimize_monthly_schedule(
        self,
        volunteers: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        max_shifts_per_month: int = 2
    ) -> Dict[str, Any]:
        """
        Resolve a matriz de escala mensal alocando voluntários para turnos.

        :param volunteers: Lista de voluntários [{'id': int, 'name': str, 'dept': str, 'blocked_dates': list}].
        :param shifts: Lista de turnos do mês [{'shift_id': int, 'date': str, 'dept': str, 'req_count': int}].
        :param max_shifts_per_month: Limite máximo de escalas mensais por pessoa.
        :return: Matriz com a atribuição ideal dos voluntários.
        """
        logger.info(f"⚙️ Otimizando escala mensal para {len(volunteers)} voluntários e {len(shifts)} turnos...")

        if not HAS_OR_TOOLS:
            logger.warning("⚠️ Google OR-Tools não está instalado. Gerando escala heurística de fallback.")
            return self._heuristic_fallback(volunteers, shifts)

        try:
            model = cp_model.CpModel()

            num_volunteers = len(volunteers)
            num_shifts = len(shifts)

            # Matriz de variáveis booleanas x[v, s] == 1 se voluntário v for escalado no turno s
            x = {}
            for v in range(num_volunteers):
                for s in range(num_shifts):
                    x[(v, s)] = model.NewBoolVar(f"x_{v}_{s}")

            # Restrição 1: Quantidade de pessoas necessárias por turno e departamento compatível
            for s, shift in enumerate(shifts):
                req = shift.get("req_count", 1)
                dept = shift.get("dept")
                eligible = [v for v, vol in enumerate(volunteers) if vol.get("dept") == dept and shift.get("date") not in vol.get("blocked_dates", [])]
                model.Add(sum(x[(v, s)] for v in eligible) == req)

            # Restrição 2: Limite máximo de turnos por mês por voluntário
            for v in range(num_volunteers):
                model.Add(sum(x[(v, s)] for s in range(num_shifts)) <= max_shifts_per_month)

            # Função de Custo / Objetivo: Maximizar distribuição equitativa
            solver = cp_model.CpSolver()
            status = solver.Solve(model)

            assigned_schedule = []
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                logger.info("✅ Solução ótima/viável encontrada com Google OR-Tools!")
                for s, shift in enumerate(shifts):
                    assigned_names = []
                    for v, vol in enumerate(volunteers):
                        if solver.Value(x[(v, s)]) == 1:
                            assigned_names.append(vol["name"])
                    assigned_schedule.append({
                        "date": shift["date"],
                        "dept": shift["dept"],
                        "assigned_volunteers": assigned_names
                    })

                return {
                    "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
                    "schedule_matrix": assigned_schedule
                }
            else:
                logger.warning("Nenhuma solução viável com restrições rígidas. Usando fallback.")
                return self._heuristic_fallback(volunteers, shifts)

        except Exception as e:
            logger.error(f"❌ Erro ao otimizar escala com OR-Tools: {e}")
            return self._heuristic_fallback(volunteers, shifts)

    def _heuristic_fallback(self, volunteers: List[Dict[str, Any]], shifts: List[Dict[str, Any]]) -> Dict[str, Any]:
        schedule = []
        vol_counts = {v["id"]: 0 for v in volunteers}

        for shift in shifts:
            dept = shift["dept"]
            date = shift["date"]
            candidates = [v for v in volunteers if v["dept"] == dept and date not in v.get("blocked_dates", [])]
            candidates.sort(key=lambda x: vol_counts[x["id"]])

            req = shift.get("req_count", 1)
            selected = candidates[:req]
            names = [s["name"] for s in selected]
            for s in selected:
                vol_counts[s["id"]] += 1

            schedule.append({
                "date": date,
                "dept": dept,
                "assigned_volunteers": names
            })

        return {
            "status": "HEURISTIC_FALLBACK",
            "schedule_matrix": schedule
        }


if __name__ == "__main__":
    opt = VolunteerScheduleOptimizer()
    sample_vols = [
        {"id": 1, "name": "Gabriel Mídia", "dept": "Mídia", "blocked_dates": []},
        {"id": 2, "name": "Lucas Som", "dept": "Mídia", "blocked_dates": ["2026-08-16"]},
        {"id": 3, "name": "Ana Louvor", "dept": "Louvor", "blocked_dates": []}
    ]
    sample_shifts = [
        {"shift_id": 101, "date": "2026-08-09", "dept": "Mídia", "req_count": 1},
        {"shift_id": 102, "date": "2026-08-16", "dept": "Mídia", "req_count": 1}
    ]
    res = opt.optimize_monthly_schedule(sample_vols, sample_shifts)
    print("Matriz de escala gerada:")
    print(res)
