"""
Simulation Laboratory Service - Manages different types of simulations.
Supports: circuit, physics, math, coding, CAD, robotics simulations.
"""
from typing import List, Dict, Optional, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import json
import logging
import subprocess
import tempfile
import os
import asyncio
from datetime import datetime

from app.models import Simulation, LearningSession, Skill
from app.config import settings

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for running and managing simulations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_simulation(self, simulation_id: UUID) -> Optional[Simulation]:
        """Get simulation by ID."""
        result = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_simulations_for_skill(self, skill_id: UUID) -> List[Simulation]:
        """Get all simulations for a skill."""
        result = await self.db.execute(
            select(Simulation).where(Simulation.skill_id == skill_id)
            .order_by(Simulation.difficulty)
        )
        return list(result.scalars().all())
    
    # ==================== Circuit Simulation (SPICE) ====================
    async def run_circuit_simulation(
        self,
        simulation: Simulation,
        config: Dict,
        analysis_type: str = "dc"
    ) -> Dict:
        """
        Run a circuit simulation using ngspice (open source SPICE).
        Returns voltages, currents, and waveforms.
        """
        # Generate SPICE netlist from config
        netlist = self._generate_spice_netlist(config)
        
        # Run ngspice
        try:
            result = await self._run_ngspice(netlist, analysis_type)
            return {
                "success": True,
                "analysis_type": analysis_type,
                "results": result,
                "netlist": netlist,
            }
        except Exception as e:
            logger.error(f"Circuit simulation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "netlist": netlist,
            }
    
    def _generate_spice_netlist(self, config: Dict) -> str:
        """Generate SPICE netlist from component configuration."""
        lines = ["* Generated Circuit Simulation", ""]
        
        # Components
        for i, comp in enumerate(config.get("components", [])):
            comp_type = comp.get("type", "R")
            name = comp.get("name", f"{comp_type}{i+1}")
            nodes = comp.get("nodes", ["1", "0"])
            value = comp.get("value", "1k")
            
            if comp_type in ["R", "C", "L"]:
                lines.append(f"{name} {nodes[0]} {nodes[1]} {value}")
            elif comp_type in ["V", "I"]:
                # Voltage/Current source
                dc_value = comp.get("dc", value)
                ac_value = comp.get("ac", "0")
                lines.append(f"{name} {nodes[0]} {nodes[1]} DC {dc_value} AC {ac_value}")
            elif comp_type in ["Q", "M"]:  # Transistors
                model = comp.get("model", "NPN")
                lines.append(f"{name} {nodes[0]} {nodes[1]} {nodes[2]} {model}")
        
        # Models
        for model_name, model_params in config.get("models", {}).items():
            lines.append(f".MODEL {model_name} {model_params}")
        
        # Analysis commands
        analysis = config.get("analysis", {})
        if analysis.get("dc"):
            lines.append(f".DC {analysis['dc']}")
        if analysis.get("ac"):
            lines.append(f".AC {analysis['ac']}")
        if analysis.get("tran"):
            lines.append(f".TRAN {analysis['tran']}")
        
        # Output
        for output in config.get("outputs", []):
            lines.append(f".PRINT {output}")
        
        lines.append(".END")
        return "\n".join(lines)
    
    async def _run_ngspice(self, netlist: str, analysis_type: str) -> Dict:
        """Run ngspice with the given netlist."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cir', delete=False) as f:
            f.write(netlist)
            netlist_path = f.name
        
        try:
            # Run ngspice in batch mode
            cmd = ["ngspice", "-b", netlist_path]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            if process.returncode != 0:
                raise Exception(f"ngspice error: {stderr.decode()}")
            
            # Parse output
            return self._parse_spice_output(stdout.decode(), analysis_type)
        
        finally:
            os.unlink(netlist_path)
    
    def _parse_spice_output(self, output: str, analysis_type: str) -> Dict:
        """Parse ngspice output."""
        # Simplified parser - in production, use a proper SPICE output parser
        lines = output.split('\n')
        results = {"raw_output": output}
        
        # Look for tabular data
        in_table = False
        headers = []
        data = []
        
        for line in lines:
            if "Index" in line and "voltage" in line.lower():
                in_table = True
                headers = line.split()
                continue
            if in_table and line.strip() and not line.startswith(" "):
                parts = line.split()
                if len(parts) == len(headers):
                    data.append(dict(zip(headers, parts)))
            elif in_table and not line.strip():
                in_table = False
        
        if data:
            results["measurements"] = data
        
        return results
    
    # ==================== Physics Simulation ====================
    async def run_physics_simulation(
        self,
        simulation: Simulation,
        config: Dict,
        duration: float = 10.0,
        dt: float = 0.01
    ) -> Dict:
        """
        Run a physics simulation (mechanics, electromagnetics, etc.).
        Uses simple numerical integration.
        """
        objects = config.get("objects", [])
        forces = config.get("forces", [])
        
        # Initialize state
        state = {
            "time": 0.0,
            "objects": [
                {
                    "id": obj.get("id", f"obj_{i}"),
                    "mass": obj.get("mass", 1.0),
                    "position": obj.get("position", [0, 0, 0]),
                    "velocity": obj.get("velocity", [0, 0, 0]),
                    "force": [0, 0, 0],
                }
                for i, obj in enumerate(objects)
            ],
        }
        
        # Simulation loop
        trajectory = []
        steps = int(duration / dt)
        
        for step in range(steps):
            # Calculate forces
            for obj in state["objects"]:
                obj["force"] = [0, 0, 0]
                
                # Apply configured forces
                for force in forces:
                    if force.get("target") == obj["id"] or force.get("target") == "all":
                        f = force.get("vector", [0, 0, 0])
                        obj["force"][0] += f[0]
                        obj["force"][1] += f[1]
                        obj["force"][2] += f[2]
                
                # Gravity
                if config.get("gravity", True):
                    obj["force"][2] -= obj["mass"] * 9.81
            
            # Integrate (Euler method)
            for obj in state["objects"]:
                # a = F/m
                ax = obj["force"][0] / obj["mass"]
                ay = obj["force"][1] / obj["mass"]
                az = obj["force"][2] / obj["mass"]
                
                # v = v + a*dt
                obj["velocity"][0] += ax * dt
                obj["velocity"][1] += ay * dt
                obj["velocity"][2] += az * dt
                
                # x = x + v*dt
                obj["position"][0] += obj["velocity"][0] * dt
                obj["position"][1] += obj["velocity"][1] * dt
                obj["position"][2] += obj["velocity"][2] * dt
            
            state["time"] = (step + 1) * dt
            
            # Record trajectory (every 10 steps)
            if step % 10 == 0:
                trajectory.append({
                    "time": state["time"],
                    "objects": [
                        {
                            "id": o["id"],
                            "position": o["position"][:],
                            "velocity": o["velocity"][:],
                        }
                        for o in state["objects"]
                    ],
                })
        
        return {
            "success": True,
            "final_state": state,
            "trajectory": trajectory,
            "duration": duration,
            "dt": dt,
        }
    
    # ==================== Math Visualization ====================
    async def run_math_visualization(
        self,
        simulation: Simulation,
        config: Dict
    ) -> Dict:
        """
        Generate mathematical visualizations (plots, vector fields, etc.).
        Returns data for frontend rendering.
        """
        viz_type = config.get("type", "function_2d")
        
        if viz_type == "function_2d":
            return self._generate_2d_function_data(config)
        elif viz_type == "function_3d":
            return self._generate_3d_function_data(config)
        elif viz_type == "vector_field":
            return self._generate_vector_field_data(config)
        elif viz_type == "complex_function":
            return self._generate_complex_function_data(config)
        else:
            return {"success": False, "error": f"Unknown visualization type: {viz_type}"}
    
    def _generate_2d_function_data(self, config: Dict) -> Dict:
        """Generate 2D function plot data."""
        import numpy as np
        
        func_str = config.get("function", "x**2")
        x_min = config.get("x_min", -10)
        x_max = config.get("x_max", 10)
        num_points = config.get("num_points", 200)
        
        x = np.linspace(x_min, x_max, num_points)
        
        # Safe evaluation of function
        try:
            # Create safe namespace
            safe_dict = {
                "x": x,
                "np": np,
                "sin": np.sin, "cos": np.cos, "tan": np.tan,
                "exp": np.exp, "log": np.log, "sqrt": np.sqrt,
                "abs": np.abs, "pi": np.pi, "e": np.e,
            }
            y = eval(func_str, {"__builtins__": {}}, safe_dict)
        except Exception as e:
            return {"success": False, "error": f"Function evaluation error: {e}"}
        
        return {
            "success": True,
            "type": "function_2d",
            "data": {
                "x": x.tolist(),
                "y": y.tolist() if hasattr(y, 'tolist') else [float(y)] * len(x),
            },
            "config": config,
        }
    
    def _generate_3d_function_data(self, config: Dict) -> Dict:
        """Generate 3D function plot data."""
        import numpy as np
        
        func_str = config.get("function", "x**2 + y**2")
        x_min = config.get("x_min", -5)
        x_max = config.get("x_max", 5)
        y_min = config.get("y_min", -5)
        y_max = config.get("y_max", 5)
        num_points = config.get("num_points", 50)
        
        x = np.linspace(x_min, x_max, num_points)
        y = np.linspace(y_min, y_max, num_points)
        X, Y = np.meshgrid(x, y)
        
        try:
            safe_dict = {
                "x": X, "y": Y,
                "np": np,
                "sin": np.sin, "cos": np.cos, "tan": np.tan,
                "exp": np.exp, "log": np.log, "sqrt": np.sqrt,
                "abs": np.abs, "pi": np.pi, "e": np.e,
            }
            Z = eval(func_str, {"__builtins__": {}}, safe_dict)
        except Exception as e:
            return {"success": False, "error": f"Function evaluation error: {e}"}
        
        return {
            "success": True,
            "type": "function_3d",
            "data": {
                "x": x.tolist(),
                "y": y.tolist(),
                "z": Z.tolist(),
            },
            "config": config,
        }
    
    def _generate_vector_field_data(self, config: Dict) -> Dict:
        """Generate 2D vector field data."""
        import numpy as np
        
        fx_str = config.get("fx", "-y")
        fy_str = config.get("fy", "x")
        x_min = config.get("x_min", -5)
        x_max = config.get("x_max", 5)
        y_min = config.get("y_min", -5)
        y_max = config.get("y_max", 5)
        grid_size = config.get("grid_size", 20)
        
        x = np.linspace(x_min, x_max, grid_size)
        y = np.linspace(y_min, y_max, grid_size)
        X, Y = np.meshgrid(x, y)
        
        try:
            safe_dict = {"x": X, "y": Y, "np": np}
            Fx = eval(fx_str, {"__builtins__": {}}, safe_dict)
            Fy = eval(fy_str, {"__builtins__": {}}, safe_dict)
        except Exception as e:
            return {"success": False, "error": f"Function evaluation error: {e}"}
        
        return {
            "success": True,
            "type": "vector_field",
            "data": {
                "x": X.tolist(),
                "y": Y.tolist(),
                "fx": Fx.tolist(),
                "fy": Fy.tolist(),
            },
            "config": config,
        }
    
    def _generate_complex_function_data(self, config: Dict) -> Dict:
        """Generate complex function visualization (domain coloring)."""
        import numpy as np
        
        func_str = config.get("function", "z**2")
        real_min = config.get("real_min", -2)
        real_max = config.get("real_max", 2)
        imag_min = config.get("imag_min", -2)
        imag_max = config.get("imag_max", 2)
        num_points = config.get("num_points", 200)
        
        real = np.linspace(real_min, real_max, num_points)
        imag = np.linspace(imag_min, imag_max, num_points)
        Real, Imag = np.meshgrid(real, imag)
        Z = Real + 1j * Imag
        
        try:
            safe_dict = {"z": Z, "np": np}
            W = eval(func_str, {"__builtins__": {}}, safe_dict)
        except Exception as e:
            return {"success": False, "error": f"Function evaluation error: {e}"}
        
        # Domain coloring: hue = argument, brightness = magnitude
        magnitude = np.abs(W)
        phase = np.angle(W)
        
        # Normalize
        magnitude_norm = np.log1p(magnitude) / np.log1p(np.max(magnitude))
        phase_norm = (phase + np.pi) / (2 * np.pi)
        
        return {
            "success": True,
            "type": "complex_function",
            "data": {
                "real": real.tolist(),
                "imag": imag.tolist(),
                "magnitude": magnitude_norm.tolist(),
                "phase": phase_norm.tolist(),
            },
            "config": config,
        }
    
    # ==================== Code Execution Sandbox ====================
    async def run_code_simulation(
        self,
        simulation: Simulation,
        config: Dict,
        user_code: str = ""
    ) -> Dict:
        """
        Run code in a Docker sandbox.
        Returns stdout, stderr, and test results.
        """
        language = config.get("language", "python")
        test_cases = config.get("test_cases", [])
        starter_code = config.get("starter_code", "")
        
        # Combine starter code with user code
        full_code = starter_code + "\n" + user_code
        
        # Run in Docker container
        return await self._run_in_sandbox(language, full_code, test_cases)
    
    async def _run_in_sandbox(
        self,
        language: str,
        code: str,
        test_cases: List[Dict]
    ) -> Dict:
        """Run code in isolated Docker container."""
        
        # Language configurations
        lang_config = {
            "python": {
                "image": "python:3.11-slim",
                "file_ext": ".py",
                "cmd": ["python", "/code/main.py"],
            },
            "javascript": {
                "image": "node:20-slim",
                "file_ext": ".js",
                "cmd": ["node", "/code/main.js"],
            },
            "cpp": {
                "image": "gcc:latest",
                "file_ext": ".cpp",
                "cmd": ["sh", "-c", "g++ -o /code/main /code/main.cpp && /code/main"],
            },
        }
        
        config = lang_config.get(language, lang_config["python"])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write code file
            code_path = os.path.join(tmpdir, f"main{config['file_ext']}")
            with open(code_path, 'w') as f:
                f.write(code)
            
            # Write test file if needed
            if test_cases:
                test_code = self._generate_test_code(language, test_cases)
                test_path = os.path.join(tmpdir, f"test{config['file_ext']}")
                with open(test_path, 'w') as f:
                    f.write(test_code)
            
            # Run Docker container
            try:
                cmd = [
                    "docker", "run", "--rm",
                    "--memory", settings.SANDBOX_MEMORY_LIMIT,
                    "--cpus", str(settings.SANDBOX_CPU_LIMIT),
                    "--network", "none",
                    "-v", f"{tmpdir}:/code",
                    "-w", "/code",
                    config["image"],
                ] + config["cmd"]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=settings.SANDBOX_TIMEOUT
                )
                
                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "return_code": process.returncode,
                    "test_results": self._parse_test_results(stdout.decode(), language),
                }
            
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": "Execution timeout",
                    "stdout": "",
                    "stderr": "Process timed out",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": str(e),
                }
    
    def _generate_test_code(self, language: str, test_cases: List[Dict]) -> str:
        """Generate test code for the given language."""
        if language == "python":
            lines = [
                "import sys",
                "import json",
                "",
                "# User's code would be imported here",
                "",
                "def run_tests():",
                "    results = []",
            ]
            for i, tc in enumerate(test_cases):
                lines.append(f"    # Test case {i+1}")
                lines.append(f"    try:")
                if "input" in tc:
                    lines.append(f"        result = solution({tc['input']})")
                else:
                    lines.append(f"        result = solution()")
                lines.append(f"        expected = {tc['expected']}")
                lines.append(f"        passed = result == expected")
                lines.append(f"        results.append({{'test': {i+1}, 'passed': passed, 'result': result, 'expected': expected}})")
                lines.append(f"    except Exception as e:")
                lines.append(f"        results.append({{'test': {i+1}, 'passed': False, 'error': str(e)}})")
            lines.append("    return results")
            lines.append("")
            lines.append("if __name__ == '__main__':")
            lines.append("    results = run_tests()")
            lines.append("    print(json.dumps(results))")
            return "\n".join(lines)
        else:
            return "// Test generation not implemented for this language"
    
    def _parse_test_results(self, output: str, language: str) -> List[Dict]:
        """Parse test results from output."""
        try:
            # Look for JSON in output
            import json
            start = output.find('[')
            end = output.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(output[start:end])
        except:
            pass
        return []
    
    # ==================== Robotics Simulation ====================
    async def run_robotics_simulation(
        self,
        simulation: Simulation,
        config: Dict
    ) -> Dict:
        """
        Run a robotics simulation (kinematics, dynamics, path planning).
        Returns robot states, sensor readings, etc.
        """
        sim_type = config.get("type", "forward_kinematics")
        
        if sim_type == "forward_kinematics":
            return self._run_forward_kinematics(config)
        elif sim_type == "inverse_kinematics":
            return self._run_inverse_kinematics(config)
        elif sim_type == "path_planning":
            return self._run_path_planning(config)
        elif sim_type == "dynamics":
            return self._run_robot_dynamics(config)
        else:
            return {"success": False, "error": f"Unknown robotics simulation type: {sim_type}"}
    
    def _run_forward_kinematics(self, config: Dict) -> Dict:
        """Calculate forward kinematics for a robot arm."""
        import numpy as np
        
        # DH parameters
        dh_params = config.get("dh_params", [])
        joint_angles = config.get("joint_angles", [])
        
        if len(dh_params) != len(joint_angles):
            return {"success": False, "error": "DH params and joint angles length mismatch"}
        
        # Transformation matrices
        T = np.eye(4)
        poses = [T.copy()]
        
        for i, (dh, theta) in enumerate(zip(dh_params, joint_angles)):
            a = dh.get("a", 0)
            alpha = dh.get("alpha", 0)
            d = dh.get("d", 0)
            
            # DH transformation matrix
            ct = np.cos(theta)
            st = np.sin(theta)
            ca = np.cos(alpha)
            sa = np.sin(alpha)
            
            T_i = np.array([
                [ct, -st*ca, st*sa, a*ct],
                [st, ct*ca, -ct*sa, a*st],
                [0, sa, ca, d],
                [0, 0, 0, 1]
            ])
            
            T = T @ T_i
            poses.append(T.copy())
        
        # Extract end-effector position and orientation
        end_effector = poses[-1]
        position = end_effector[:3, 3].tolist()
        rotation = end_effector[:3, :3].tolist()
        
        return {
            "success": True,
            "type": "forward_kinematics",
            "joint_positions": [p[:3, 3].tolist() for p in poses],
            "end_effector_position": position,
            "end_effector_rotation": rotation,
            "all_poses": [p.tolist() for p in poses],
        }
    
    def _run_inverse_kinematics(self, config: Dict) -> Dict:
        """Calculate inverse kinematics (simplified)."""
        # This is a placeholder - real IK needs numerical solvers
        target_position = config.get("target_position", [0, 0, 0])
        dh_params = config.get("dh_params", [])
        
        return {
            "success": True,
            "type": "inverse_kinematics",
            "message": "IK solver not fully implemented - use numerical optimization",
            "target_position": target_position,
            "note": "Implement using scipy.optimize or similar",
        }
    
    def _run_path_planning(self, config: Dict) -> Dict:
        """Run path planning (RRT, A*, etc.)."""
        # Placeholder for path planning
        return {
            "success": True,
            "type": "path_planning",
            "message": "Path planning not fully implemented",
            "note": "Implement RRT, A*, or use OMPL",
        }
    
    def _run_robot_dynamics(self, config: Dict) -> Dict:
        """Run robot dynamics simulation."""
        # Placeholder for dynamics
        return {
            "success": True,
            "type": "dynamics",
            "message": "Dynamics simulation not fully implemented",
            "note": "Implement using Lagrangian dynamics or use Pinocchio/Drake",
        }
    
    # ==================== Main Entry Point ====================
    async def run_simulation(
        self,
        simulation_id: UUID,
        config: Dict,
        user_input: Optional[Dict] = None
    ) -> Dict:
        """Main entry point to run any simulation."""
        simulation = await self.get_simulation(simulation_id)
        if not simulation:
            return {"success": False, "error": "Simulation not found"}
        
        # Merge configs
        full_config = simulation.config.copy()
        full_config.update(config)
        if user_input:
            full_config.update(user_input)
        
        # Route to appropriate simulator
        if simulation.simulation_type == "circuit":
            return await self.run_circuit_simulation(simulation, full_config)
        elif simulation.simulation_type == "physics":
            return await self.run_physics_simulation(simulation, full_config)
        elif simulation.simulation_type == "math":
            return await self.run_math_visualization(simulation, full_config)
        elif simulation.simulation_type == "coding":
            user_code = user_input.get("code", "") if user_input else ""
            return await self.run_code_simulation(simulation, full_config, user_code)
        elif simulation.simulation_type == "robotics":
            return await self.run_robotics_simulation(simulation, full_config)
        else:
            return {"success": False, "error": f"Unknown simulation type: {simulation.simulation_type}"}