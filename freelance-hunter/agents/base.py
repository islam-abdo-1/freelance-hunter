"""
Base agent class for Freelance Hunter.
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool
    data: Any = None
    error: str = None
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    items_found: int = 0
    items_processed: int = 0


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(self, name: str, config: dict[str, Any] | None = None, db_manager=None):
        self.name = name
        self.config = config or {}
        self.db_manager = db_manager
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"agent.{name}")
        self._start_time: float | None = None
        self._results: list[AgentResult] = []
    
    @abstractmethod
    async def execute(self, **kwargs) -> AgentResult:
        """Execute the agent's main task."""
    
    async def run(self, **kwargs) -> AgentResult:
        """Run the agent with timing and error handling."""
        self.status = AgentStatus.RUNNING
        self._start_time = time.time()
        self.logger.info(f"Starting agent: {self.name}")
        
        try:
            result = await self.execute(**kwargs)
            self._results.append(result)
            
            execution_time = time.time() - self._start_time
            result.execution_time = execution_time
            
            if result.success:
                self.status = AgentStatus.COMPLETED
                self.logger.info(
                    f"Agent {self.name} completed in {execution_time:.2f}s "
                    f"(found: {result.items_found}, processed: {result.items_processed})"
                )
            else:
                self.status = AgentStatus.FAILED
                self.logger.error(f"Agent {self.name} failed: {result.error}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - self._start_time
            error_msg = str(e)
            self.logger.exception(f"Agent {self.name} crashed: {error_msg}")
            self.status = AgentStatus.FAILED
            
            result = AgentResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
            self._results.append(result)
            return result
    
    def get_last_result(self) -> AgentResult | None:
        """Get the last execution result."""
        return self._results[-1] if self._results else None
    
    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        total_runs = len(self._results)
        successful_runs = sum(1 for r in self._results if r.success)
        total_items = sum(r.items_found for r in self._results)
        total_time = sum(r.execution_time for r in self._results)
        
        return {
            "name": self.name,
            "status": self.status.value,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "total_items_found": total_items,
            "total_execution_time": total_time,
            "avg_execution_time": total_time / total_runs if total_runs > 0 else 0,
            "last_run": self._results[-1].execution_time if self._results else None
        }
    
    def reset_stats(self):
        """Reset agent statistics."""
        self._results.clear()
        self.status = AgentStatus.IDLE


class AgentOrchestrator:
    """Orchestrates multiple agents."""
    
    def __init__(self, config: dict[str, Any] | None = None, db_manager=None):
        self.config = config or {}
        self.db_manager = db_manager
        self.agents: dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("orchestrator")
        self.execution_history: list[dict[str, Any]] = []
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent."""
        self.agents[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, name: str) -> BaseAgent | None:
        """Get agent by name."""
        return self.agents.get(name)
    
    async def run_agent(self, name: str, **kwargs) -> AgentResult:
        """Run a single agent."""
        agent = self.get_agent(name)
        if not agent:
            return AgentResult(success=False, error=f"Agent '{name}' not found")
        
        result = await agent.run(**kwargs)
        
        # Record execution
        self.execution_history.append({
            "agent": name,
            "timestamp": datetime.utcnow().isoformat(),
            "success": result.success,
            "execution_time": result.execution_time,
            "items_found": result.items_found,
            "error": result.error
        })
        
        return result
    
    async def run_agents_parallel(self, agent_names: list[str], **kwargs) -> dict[str, AgentResult]:
        """Run multiple agents in parallel."""
        tasks = {}
        for name in agent_names:
            agent = self.get_agent(name)
            if agent:
                tasks[name] = agent.run(**kwargs)
            else:
                self.logger.warning(f"Agent '{name}' not found, skipping")
        
        results = {}
        if tasks:
            done = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for (name, _), result in zip(tasks.items(), done):
                if isinstance(result, Exception):
                    results[name] = AgentResult(success=False, error=str(result))
                else:
                    results[name] = result
                    
                    # Record execution
                    self.execution_history.append({
                        "agent": name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": result.success,
                        "execution_time": result.execution_time,
                        "items_found": result.items_found,
                        "error": result.error
                    })
        
        return results
    
    async def run_agents_sequential(self, agent_names: list[str], **kwargs) -> dict[str, AgentResult]:
        """Run multiple agents sequentially."""
        results = {}
        for name in agent_names:
            result = await self.run_agent(name, **kwargs)
            results[name] = result
            
            # Stop on failure if configured
            if not result.success and self.config.get("stop_on_failure", False):
                self.logger.warning(f"Stopping sequential execution due to failure in {name}")
                break
        
        return results
    
    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all agents."""
        return {name: agent.get_stats() for name, agent in self.agents.items()}
    
    def get_execution_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get execution history."""
        return self.execution_history[-limit:]