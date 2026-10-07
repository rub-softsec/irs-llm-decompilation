import math
import json
from pathlib import Path
import subprocess
from typing import Optional, Tuple
import tempfile
import contextlib
import os
import shutil
import glob
import re
from ast import literal_eval

__all__ = ['diff_io', 'Wrapper', 'binarytest_dict_to_dict']

__version__ = 0.1

# UTILS (in a self-contained file to ease deployment)

_DEFAULT_CMD_TIMEOUT = 60
_ROOT_PATH_FOR_JSON_HPP = os.path.dirname(__file__)
_SYNTH_LIBS_PATH = os.path.dirname(__file__)


def _run_command(command: str, stdin: Optional[str] = None, timeout: Optional[int] = _DEFAULT_CMD_TIMEOUT) -> Tuple[str, str]:
    output = subprocess.run(command.split(), capture_output=True, text=True, input=stdin, timeout=timeout)
    stdout = output.stdout.decode('utf-8') if isinstance(output.stdout, bytes) else output.stdout
    stderr = output.stderr.decode('utf-8') if isinstance(output.stderr, bytes) else output.stderr
    return stdout, stderr


def _get_host_process_id():
    process_id = 'binarytest_' + os.uname()[1] + '_' + str(os.getpid())
    return process_id


def _cleanup(path_pattern):
    for path in glob.glob(path_pattern):
        try:
            shutil.rmtree(path)
        except:
            pass


@contextlib.contextmanager
def _get_tmp_path(content: Optional[str] = None, suffix: Optional[str] = None, delete=True) -> str:
    prefix = _get_host_process_id()
    try:
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=delete, mode='w+') as ntf:
            if content:
                ntf.write(content)
                ntf.flush()
            yield ntf.name
    except OSError:
        _cleanup(os.path.join(tempfile.gettempdir(), prefix, '*'))
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=delete, mode='w+') as ntf:
            if content:
                ntf.write(content)
                ntf.flush()
            yield ntf.name


class _Assembler:
    def __call__(self, c_deps, func_c_signature, func_assembly, cpp_wrapper) -> Path:
        raise NotImplemented


class _DefaultAssembler(_Assembler):
    def __call__(self, c_deps, func_c_signature, func_assembly, cpp_wrapper) -> Path:
        with _get_tmp_path(content=None, suffix='.x', delete=False) as executable_path:
            c_deps += f'\nextern {func_c_signature};\n'
            with _get_tmp_path(content=c_deps, suffix='.c') as c_deps_path:
                cpp_wrapper = re.sub(
                    r'extern\s\"C\"\s\{\s.*\s\}', 'extern "C" \n{\n#include "' + c_deps_path + '"\n}\n',
                    cpp_wrapper) # replace tmp path
                with _get_tmp_path(content=cpp_wrapper, suffix='.cpp') as cpp_path, \
                        _get_tmp_path(content=func_assembly, suffix='.s') as s_path:

                    cmd = f'g++ -fpermissive -O0 -o {executable_path} {cpp_path} {s_path} -I {_ROOT_PATH_FOR_JSON_HPP} -I{_SYNTH_LIBS_PATH} -I.. -I../nlohmann -I.'

                    stdout, stderr = _run_command(cmd)

        return Path(executable_path)


class _CCompiler(_Assembler):
    def __call__(self, c_deps, func_c_signature, func_c_code, cpp_wrapper) -> Path:
        """Compile C code directly instead of assembly"""
        with _get_tmp_path(content=None, suffix='.x', delete=False) as executable_path:
            # Combine c_deps with the function C code
            combined_c_code = c_deps + "\n" + func_c_code

            with _get_tmp_path(content=combined_c_code, suffix='.c') as c_code_path:
                # Update the cpp_wrapper to include the C code file
                cpp_wrapper = re.sub(
                    r'extern\s\"C\"\s\{\s.*\s\}', 'extern "C" \n{\n#include "' + c_code_path + '"\n}\n',
                    cpp_wrapper)
                
                with _get_tmp_path(content=cpp_wrapper, suffix='.cpp') as cpp_path:
                    # Compile both C and C++ code together
                    print("---------------------------------------------------------")
                    print(_ROOT_PATH_FOR_JSON_HPP)
                    print("---------------------------------------------------------")
                    cmd = f'g++ -fpermissive -O0 -o {executable_path} {cpp_path} -I {_ROOT_PATH_FOR_JSON_HPP} -I{_SYNTH_LIBS_PATH} -I.. -I../nlohmann -I.'
                    
                    stdout, stderr = _run_command(cmd)
                    if stderr:
                        print(f"Compilation errors: {stderr}")

        return Path(executable_path)


def _compile_exe_path(c_deps, func_c_signature, func_assembly, cpp_wrapper, assembler_backend):
    return assembler_backend(c_deps, func_c_signature, func_assembly, cpp_wrapper)


def _compile_c_exe_path(c_deps, func_c_signature, func_c_code, cpp_wrapper, compiler_backend):
    return compiler_backend(c_deps, func_c_signature, func_c_code, cpp_wrapper)


# API

class Wrapper:
    def __init__(self, c_deps, func_c_signature, func_assembly=None, func_c_code=None, cpp_wrapper=None, assembler_backend=None):
        """
        Initialize the Wrapper for assembly code or C code.
        
        Args:
            c_deps: C dependencies/headers needed
            func_c_signature: The C function signature
            func_assembly: The assembly code (optional if func_c_code is provided)
            func_c_code: The C function code (optional if func_assembly is provided)
            cpp_wrapper: C++ wrapper code that calls the function
            assembler_backend: The compiler/assembler to use
        """
        if func_assembly is not None and cpp_wrapper is not None:
            # Assembly mode (original)
            if assembler_backend is None:
                assembler_backend = _DefaultAssembler()
            self._compiled_exe_path = self._compile_exe_path(c_deps, func_c_signature, func_assembly, cpp_wrapper, assembler_backend)
        elif func_c_code is not None and cpp_wrapper is not None:
            # C code mode (new)
            if assembler_backend is None:
                assembler_backend = _CCompiler()
            self._compiled_exe_path = self._compile_c_exe_path(c_deps, func_c_signature, func_c_code, cpp_wrapper, assembler_backend)
        else:
            raise ValueError("You must provide either func_assembly or func_c_code along with cpp_wrapper")

    @staticmethod
    def _compile_exe_path(c_deps, func_c_signature, func_assembly, cpp_wrapper, assembler_backend):
        return _compile_exe_path(c_deps, func_c_signature, func_assembly, cpp_wrapper, assembler_backend)
    
    @staticmethod
    def _compile_c_exe_path(c_deps, func_c_signature, func_c_code, cpp_wrapper, compiler_backend):
        return _compile_c_exe_path(c_deps, func_c_signature, func_c_code, cpp_wrapper, compiler_backend)

    def __call__(self, inp, return_stdout_and_stderr=False):
        executable = self._compiled_exe_path

        with _get_tmp_path(content=None, suffix='.json') as input_tmp_json_path:
            output_file = ''.join(input_tmp_json_path.split(".")[:1]) + '-out.json'

            with open(input_tmp_json_path, 'w') as f:
                json.dump(inp, f)

            stdout, stderr = _run_command(f'{executable} {input_tmp_json_path} {output_file}')

            with open(output_file, 'r') as f:
                output = json.load(f)
            os.remove(output_file)

        if return_stdout_and_stderr:
            return output, stdout, stderr

        return output


def diff_io(observed_output, expected_output) -> bool:
    if type(observed_output) is not type(expected_output):
        return False
    if isinstance(observed_output, list):
        if len(observed_output) != len(expected_output):
            return False
        for e1, e2 in zip(observed_output, expected_output):
            ok = diff_io(e1, e2)
            if not ok:
                return False
    elif isinstance(observed_output, dict):
        for key in observed_output:
            if key not in expected_output:
                return False
            ok = diff_io(observed_output[key], expected_output[key])
            if not ok:
                return False
    elif isinstance(observed_output, float):
        ok = math.isclose(observed_output, expected_output)
        if not ok:
            return False
    else:
        ok = observed_output == expected_output
        if not ok:
            return False
    return True


def binarytest_dict_to_dict(exebench_dict):
    """Convert exebench format to binarytest format if needed"""
    return exebench_dict