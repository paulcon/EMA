"""The model spec's JSON form: ``from_json``, ``to_json``, ``versioned_json`` (architecture.md §3, model.py).

The checks that need no file (model_interface.md, The model spec; M18, M21; trust.md T2's spec checks, T7, T8;
data_model.md §3.4's defaults filled in), each refusal naming its field.
"""

import json
import math

import pytest

from ema.types.errors import SpecError
from ema.types.model import (
    CREDENTIAL_WORDS,
    EMA_FILE_NAMES,
    CommandLine,
    CsvParser,
    FileEntry,
    InputDeck,
    JsonParser,
    Keep,
    Limits,
    ModelSpec,
    PythonFunction,
    RegexParser,
    hidden_character,
    is_credentials_file,
)

#: U2's heat solver, as model_interface.md writes it.
HEAT = {
    "name": "heat",
    "description": "2-D steady heat conduction in a plate",
    "interface": "command_line",
    "command": ["./heat_solver", "plate.in"],
    "input_decks": [{"template": "plate.in.template", "writes": "plate.in"}],
    "files": ["heat_solver", "solver.cfg", {"path": "mesh.dat", "shared": True}],
    "env": {"OMP_NUM_THREADS": "4"},
    "parameters": [
        {
            "name": "k",
            "units": "W/(m K)",
            "nominal": 45.0,
            "description": "thermal conductivity",
            "limits": {"gt": 0},
        },
        {"name": "q", "units": "W/m^2", "nominal": 3e4, "description": "heat flux"},
    ],
    "predictions": [
        {
            "name": "T_max",
            "units": "K",
            "description": "peak temperature",
            "parser": {"kind": "regex", "file": "plate.out", "pattern": "T_max = (\\S+)"},
        }
    ],
    "timeout_s": 600,
    "keep": "incomplete",
}

#: U1's beam, as model_interface.md writes it.
BEAM = {
    "name": "beam",
    "description": "tip deflection of a cantilever beam",
    "interface": "python_function",
    "function": "beam.py:deflection",
    "parameters": [
        {"name": "E", "units": "Pa", "nominal": 2e11, "description": "Young's modulus", "limits": {"gt": 0}},
        {"name": "L", "units": "m", "nominal": 1.5, "description": "length", "limits": {"gt": 0}},
        {"name": "P", "units": "N", "nominal": 3e3, "description": "tip load"},
    ],
    "predictions": [{"name": "delta", "units": "m", "description": "tip deflection"}],
}


def text(spec: dict) -> str:
    return json.dumps(spec)


def edited(base: dict, **changes) -> str:
    spec = json.loads(json.dumps(base))
    for key, value in changes.items():
        if value is ...:
            del spec[key]
        else:
            spec[key] = value
    return json.dumps(spec)


def refused(spec_text: str, *fragments: str) -> str:
    with pytest.raises(SpecError) as info:
        ModelSpec.from_json(spec_text)
    message = str(info.value)
    for fragment in fragments:
        assert fragment in message, f"{fragment!r} not in {message!r}"
    return message


class TestKnownSpecs:
    def test_heat(self):
        spec = ModelSpec.from_json(text(HEAT))
        assert spec.name == "heat"
        assert spec.interface == CommandLine(
            command=("./heat_solver", "plate.in"), input_decks=(InputDeck("plate.in.template", "plate.in"),)
        )
        assert spec.files == (FileEntry("heat_solver"), FileEntry("solver.cfg"), FileEntry("mesh.dat", shared=True))
        assert dict(spec.env) == {"OMP_NUM_THREADS": "4"} and spec.pass_env == ()
        k = spec.parameter("k")
        assert k.limits == Limits(lower=0.0, lower_strict=True) and type(k.nominal) is float
        assert spec.parameter("q").limits == Limits()
        assert spec.prediction(None).parser == RegexParser(file="plate.out", pattern="T_max = (\\S+)", match="last")
        assert spec.keep is Keep.INCOMPLETE and spec.timeout_s == 600.0 and type(spec.timeout_s) is float
        assert spec.batch_size is None and spec.noisy is False

    def test_beam(self):
        spec = ModelSpec.from_json(text(BEAM))
        assert spec.interface == PythonFunction(function="beam.py:deflection", batch=False)
        assert [p.name for p in spec.parameters] == ["E", "L", "P"]
        assert spec.prediction(None).parser is None
        assert spec.keep is Keep.ALL and spec.timeout_s == 3600.0 and spec.files == ()

    def test_the_other_parsers(self):
        heat = json.loads(text(HEAT))
        heat["predictions"] = [
            {"name": "a", "units": "", "description": "", "parser": {"kind": "json", "file": "o.json", "key": "x.0.y"}},
            {"name": "b", "units": "", "description": "", "parser": {"kind": "csv", "file": "o.csv", "column": 2}},
            {
                "name": "c",
                "units": "",
                "description": "",
                "parser": {"kind": "csv", "file": "o.csv", "column": "T", "row": 0, "delimiter": "\t"},
            },
            {
                "name": "d",
                "units": "",
                "description": "",
                "parser": {"kind": "regex", "file": "stdout", "pattern": "T = (?P<value>\\S+)", "match": "first"},
            },
        ]
        spec = ModelSpec.from_json(json.dumps(heat))
        assert [p.parser for p in spec.predictions] == [
            JsonParser(file="o.json", key="x.0.y"),
            CsvParser(file="o.csv", column=2),
            CsvParser(file="o.csv", column="T", row=0, delimiter="\t"),
            RegexParser(file="stdout", pattern="T = (?P<value>\\S+)", match="first"),
        ]

    def test_batch_and_settings(self):
        spec = ModelSpec.from_json(edited(BEAM, batch=True, batch_size=3, keep="none", timeout_s=0.5))
        assert spec.interface == PythonFunction("beam.py:deflection", batch=True)
        assert spec.batch_size == 3 and spec.keep is Keep.NONE and spec.timeout_s == 0.5

    def test_pass_env_and_paths_normalized(self):
        spec = ModelSpec.from_json(
            edited(BEAM, function="./src//beam.py:deflection", files=["./mesh.dat"], pass_env=["LM_LICENSE_FILE"])
        )
        assert spec.interface.function == "src/beam.py:deflection"
        assert spec.files == (FileEntry("mesh.dat"),)
        assert spec.pass_env == ("LM_LICENSE_FILE",)


class TestRoundTrip:
    @pytest.mark.parametrize("base", [HEAT, BEAM])
    def test_to_json_reads_back_equal(self, base):
        spec = ModelSpec.from_json(text(base))
        again = ModelSpec.from_json(spec.to_json())
        assert again == spec
        assert again.to_json() == spec.to_json()

    def test_to_json_writes_every_field_with_defaults(self):
        data = json.loads(ModelSpec.from_json(text(BEAM)).to_json())
        assert data["batch"] is False and data["batch_size"] is None and data["noisy"] is False
        assert data["env"] == {} and data["pass_env"] == [] and data["files"] == []
        assert data["keep"] == "all" and data["timeout_s"] == 3600.0
        assert data["parameters"][2]["limits"] == {} and data["parameters"][0]["limits"] == {"gt": 0.0}
        assert "command" not in data and "parser" not in data["predictions"][0]
        heat = json.loads(ModelSpec.from_json(text(HEAT)).to_json())
        assert heat["files"][0] == {"path": "heat_solver", "shared": False}
        assert heat["predictions"][0]["parser"]["match"] == "last"
        assert "function" not in heat and "batch" not in heat

    def test_to_json_is_readable_text(self):
        out = ModelSpec.from_json(text(HEAT)).to_json()
        assert out.endswith("}\n") and out.startswith('{\n  "name": "heat",')

    def test_versioned_json_leaves_out_the_settings(self):
        spec = ModelSpec.from_json(text(HEAT))
        data = json.loads(spec.versioned_json())
        assert not {"keep", "batch_size", "timeout_s"} & set(data)
        assert spec.versioned_json() == json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert ModelSpec.from_json(spec.versioned_json()).versioned_json() == spec.versioned_json()

    def test_a_default_written_out_or_left_out_is_one_versioned_json(self):
        """M3, data_model.md §3.4."""
        left_out = ModelSpec.from_json(text(BEAM))
        written = ModelSpec.from_json(
            edited(BEAM, batch=False, files=[], env={}, pass_env=[], noisy=False, keep="all", timeout_s=3600)
        )
        assert left_out.versioned_json() == written.versioned_json()
        heat = json.loads(text(HEAT))
        heat["files"] = [{"path": "heat_solver", "shared": False}, "solver.cfg", {"path": "mesh.dat", "shared": True}]
        heat["predictions"][0]["parser"]["match"] = "last"
        heat["parameters"][0]["nominal"] = 45
        heat["timeout_s"] = 1
        assert (
            ModelSpec.from_json(json.dumps(heat)).versioned_json() == ModelSpec.from_json(text(HEAT)).versioned_json()
        )

    def test_doubles_round_trip(self):
        beam = json.loads(text(BEAM))
        beam["parameters"][2]["nominal"] = -0.0
        beam["parameters"][1]["nominal"] = 5e-324
        spec = ModelSpec.from_json(ModelSpec.from_json(json.dumps(beam)).to_json())
        assert math.copysign(1.0, spec.parameter("P").nominal) == -1.0
        assert spec.parameter("L").nominal == 5e-324


class TestRequiredAndUnknown:
    @pytest.mark.parametrize("key", ["name", "description", "interface", "parameters", "predictions", "function"])
    def test_required(self, key):
        refused(edited(BEAM, **{key: ...}), key, "required")

    def test_command_required(self):
        refused(edited(HEAT, command=...), "command", "required")

    def test_unknown_key_named(self):
        refused(edited(BEAM, colour="red"), "colour")
        beam = json.loads(text(BEAM))
        beam["parameters"][0]["scale"] = "log"
        refused(json.dumps(beam), "parameters[0].scale")

    @pytest.mark.parametrize(
        ("base", "key", "value"),
        [
            (BEAM, "command", ["x"]),
            (BEAM, "input_decks", []),
            (HEAT, "function", "f.py:f"),
            (HEAT, "batch", False),
        ],
    )
    def test_the_other_interfaces_fields_refused(self, base, key, value):
        refused(edited(base, **{key: value}), key)

    def test_batch_size_only_for_a_batch(self):
        refused(edited(BEAM, batch_size=3), "batch_size")
        refused(edited(HEAT, batch_size=3), "batch_size")
        ModelSpec.from_json(edited(HEAT, batch_size=None))

    def test_parsers(self):
        beam = json.loads(text(BEAM))
        beam["predictions"][0]["parser"] = {"kind": "json", "file": "o.json", "key": "x"}
        refused(json.dumps(beam), "predictions[0].parser")
        heat = json.loads(text(HEAT))
        del heat["predictions"][0]["parser"]
        refused(json.dumps(heat), "predictions[0].parser", "required")

    @pytest.mark.parametrize(
        "parser",
        [
            {"kind": "xml", "file": "o"},
            {"kind": "regex", "file": "o", "pattern": "no group"},
            {"kind": "regex", "file": "o", "pattern": "(a)(b)"},
            {"kind": "regex", "file": "o", "pattern": "(unclosed"},
            {"kind": "regex", "file": "o", "pattern": "(x)", "match": "middle"},
            {"kind": "json", "file": "o", "key": "a..b"},
            {"kind": "json", "file": "o", "key": ""},
            {"kind": "csv", "file": "o", "column": True},
            {"kind": "csv", "file": "o", "column": 1, "row": 1.5},
            {"kind": "csv", "file": "o", "column": 1, "delimiter": ";;"},
            {"kind": "json", "file": "../o.json", "key": "x"},
            {"kind": "json", "file": "/tmp/o.json", "key": "x"},
            {"kind": "json", "file": "o.json"},
        ],
    )
    def test_bad_parsers(self, parser):
        heat = json.loads(text(HEAT))
        heat["predictions"][0]["parser"] = parser
        refused(json.dumps(heat), "predictions[0].parser")

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("name", 3),
            ("description", None),
            ("parameters", []),
            ("predictions", {}),
            ("files", "mesh.dat"),
            ("env", ["A"]),
            ("pass_env", "A"),
            ("keep", "some"),
            ("timeout_s", 0),
            ("timeout_s", True),
            ("noisy", "no"),
            ("interface", "fortran"),
            ("interface", ["python_function"]),
            ("keep", ["all"]),
        ],
    )
    def test_wrong_types(self, key, value):
        refused(edited(BEAM, **{key: value}), key)

    def test_batch_size_values(self):
        for bad in (0, -1, 2.5, True, "3"):
            refused(edited(BEAM, batch=True, batch_size=bad), "batch_size")
        assert ModelSpec.from_json(edited(BEAM, batch=True, batch_size=4.0)).batch_size == 4

    def test_not_json_or_not_an_object(self):
        refused("{", "not JSON")
        refused("[]", "object")
        refused('{"name": NaN}', "NaN")


class TestNamesAndValues:
    @pytest.mark.parametrize("name", ["Heat", "heat solver", "", "heat.v2", "héat"])
    def test_model_name(self, name):
        refused(edited(BEAM, name=name), "name")

    def test_model_name_allowed(self):
        assert ModelSpec.from_json(edited(BEAM, name="heat-2d_v3")).name == "heat-2d_v3"

    @pytest.mark.parametrize("name", ["1k", "k-1", "lambda", "", "a b"])
    def test_parameter_names_are_identifiers(self, name):
        beam = json.loads(text(BEAM))
        beam["parameters"][0]["name"] = name
        refused(json.dumps(beam), "parameters[0].name")

    def test_soft_keywords_allowed(self):
        beam = json.loads(text(BEAM))
        beam["parameters"][0]["name"] = "match"
        assert ModelSpec.from_json(json.dumps(beam)).parameters[0].name == "match"

    def test_names_unique_across_both_lists(self):
        beam = json.loads(text(BEAM))
        beam["predictions"][0]["name"] = "L"
        refused(json.dumps(beam), "predictions[0].name", "L")
        beam = json.loads(text(BEAM))
        beam["parameters"][1]["name"] = "E"
        refused(json.dumps(beam), "parameters[1].name", "E")

    def test_m21_the_ema_prefix_refused(self):
        """M21 (0053): as M18's test is for noisy."""
        beam = json.loads(text(BEAM))
        beam["predictions"][0]["name"] = "ema_status"
        refused(json.dumps(beam), "predictions[0].name", "ema_status", "ema_")
        beam = json.loads(text(BEAM))
        beam["parameters"][0]["name"] = "ema_x"
        refused(json.dumps(beam), "parameters[0].name", "ema_x")

    def test_m18_noisy_true_refused(self):
        refused(edited(BEAM, noisy=True), "noisy", "later version")

    def test_nominal_inside_limits(self):
        beam = json.loads(text(BEAM))
        beam["parameters"][0]["nominal"] = 0
        refused(json.dumps(beam), "parameters[0]", "gt 0.0")
        beam["parameters"][0]["limits"] = {"ge": 0, "le": 1}
        assert ModelSpec.from_json(json.dumps(beam)).parameters[0].limits == Limits(lower=0.0, upper=1.0)

    @pytest.mark.parametrize(
        "limits", [{"gt": 0, "ge": 0}, {"lt": 1, "le": 1}, {"gt": "0"}, {"gt": True}, {"between": [0, 1]}, [0, 1]]
    )
    def test_bad_limits(self, limits):
        beam = json.loads(text(BEAM))
        beam["parameters"][2]["limits"] = limits
        refused(json.dumps(beam), "parameters[2].limits")

    @pytest.mark.parametrize("nominal", ["45", True, None, 1e400])
    def test_bad_nominal(self, nominal):
        beam = json.loads(text(BEAM))
        beam["parameters"][2]["nominal"] = nominal
        refused(json.dumps(beam).replace("Infinity", "1e400"), "parameters[2].nominal")

    def test_function_shape(self):
        for bad in ("beam.py", "beam.py:", "beam:deflection", "beam.py:not-a-name", "beam.py:class", ":f"):
            refused(edited(BEAM, function=bad), "function")

    def test_command(self):
        refused(edited(HEAT, command=[]), "command")
        refused(edited(HEAT, command=[""]), "command")
        refused(edited(HEAT, command=["x", 3]), "command[1]")
        assert ModelSpec.from_json(edited(HEAT, command=["/usr/bin/env", "x"])).interface.command[0] == "/usr/bin/env"


class TestTrustT7:
    """trust.md T7: paths, credentials files, EMA's own names, hidden characters, duplicate keys."""

    @pytest.mark.parametrize("path", ["../x", "a/../../x", "/etc/hosts", ".env", ".ssh/id_rsa", "db-credentials.json"])
    def test_files_refused(self, path):
        refused(edited(HEAT, files=[path]), "files[0]")

    def test_a_path_outside_names_the_link_workaround(self):
        message = refused(edited(HEAT, files=["../mesh.h5"]), "files[0]", "link")
        assert "directory" in message

    @pytest.mark.parametrize("path", [".env.example", "secretion.py", "deck.key", "keys.csv", "token_bucket.py"])
    def test_ordinary_files_load(self, path):
        assert ModelSpec.from_json(edited(HEAT, files=[path])).files == (FileEntry(path),)

    @pytest.mark.parametrize("name", EMA_FILE_NAMES + ("RUN.JSON",))
    def test_ema_own_names_refused(self, name):
        refused(edited(HEAT, files=[name]), "files[0]", name)
        refused(edited(HEAT, input_decks=[{"template": "t", "writes": name}]), "input_decks[0].writes")

    def test_own_names_below_a_directory_load(self):
        assert ModelSpec.from_json(edited(HEAT, files=["out/run.json"])).files == (FileEntry("out/run.json"),)

    def test_other_paths(self):
        refused(edited(BEAM, function="../beam.py:f"), "function")
        refused(edited(BEAM, function=".env.py:f"), "function")
        refused(edited(HEAT, input_decks=[{"template": "/t", "writes": "x"}]), "input_decks[0].template")
        refused(edited(HEAT, input_decks=[{"template": "t", "writes": "../x"}]), "input_decks[0].writes")
        refused(edited(HEAT, input_decks=[{"template": "secret.tmpl", "writes": "x"}]), "input_decks[0].template")
        refused(edited(HEAT, files=[""]), "files[0]")
        refused(edited(HEAT, files=[{"path": "a", "shared": "yes"}]), "files[0].shared")
        refused(edited(HEAT, files=[{"shared": True}]), "files[0].path")

    def test_duplicates_and_collisions(self):
        refused(edited(HEAT, files=["a", "./a"]), "files[1]")
        decks = [{"template": "t1", "writes": "x"}, {"template": "t2", "writes": "x"}]
        refused(edited(HEAT, input_decks=decks), "input_decks[1].writes")
        refused(edited(HEAT, input_decks=[{"template": "t", "writes": "a"}], files=["a"]), "input_decks[0].writes")
        both = ModelSpec.from_json(edited(HEAT, input_decks=[{"template": "t", "writes": "x"}], files=["t"]))
        assert both.files == (FileEntry("t"),)

    @pytest.mark.parametrize(
        ("where", "bad"),
        [
            ("command[0]", "\x1b[2K"),
            ("description", "a\u202eb"),
            ("description", "two\nlines"),
            ("description", "a\u2028b"),
            ("name", "\ud800"),
            ("parameters[0].units", "\u200b"),
        ],
    )
    def test_hidden_characters_refused(self, where, bad):
        spec = json.loads(text(HEAT))
        if where == "command[0]":
            spec["command"][0] = bad
        elif where == "parameters[0].units":
            spec["parameters"][0]["units"] = bad
        else:
            spec[where] = bad
        refused(json.dumps(spec), where, "U+")

    def test_hidden_character_in_a_key(self):
        refused(edited(HEAT, env={"A\u202e": "1"}), "env")

    def test_tab_and_joiners_allowed(self):
        spec = ModelSpec.from_json(edited(BEAM, description="tab\there, joiners \u200c\u200d"))
        assert "\t" in spec.description

    def test_duplicate_keys_refused(self):
        dup = text(HEAT).replace('"command":', '"command": ["x"], "command":')
        refused(dup, "command", "twice")
        dup = text(HEAT).replace('"units": "K"', '"units": "K", "units": "C"')
        refused(dup, "predictions[0].units", "twice")

    def test_hidden_character_function(self):
        assert hidden_character("plain\ttext \u200d") is None
        assert hidden_character("a\u202eb") == "\u202e"
        assert hidden_character("\x00") == "\x00"


class TestCredentialsFiles:
    """v1's is_secret cases, rewritten (trust.md, Paths; 0057 item 4)."""

    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".ENV",
            "prod.env",
            ".env.local",
            ".envrc",
            ".ssh/id_rsa",
            ".SSH/id_rsa",
            ".Ssh/config",
            "id_rsa",
            "id_ed25519",
            "ID_ECDSA",
            ".netrc",
            ".pgpass",
            "gcloud/application_default_credentials.json",
            ".config/gcloud/configurations/config_default",
            ".CONFIG/GH/hosts.yml",
            ".aws/config",
            "a/b/.gnupg/pubring.kbx",
            "client_secret.json",
            "db-credentials.json",
            "credentials",
            "server.pem",
            "putty.ppk",
            "cert.P12",
            ".zshrc",
            ".bash_history",
            ".git-credentials",
        ],
    )
    def test_recognized_in_any_case(self, path):
        assert is_credentials_file(path)

    @pytest.mark.parametrize(
        "path",
        [
            "deck.txt",
            ".env.example",
            ".env.sample",
            ".env.template",
            "secretion.py",
            "deck.key",
            "token_bucket.py",
            "model.json",
            "keys.csv",
            "ssh/config",
            "config/gcloud.txt",
        ],
    )
    def test_ordinary_files(self, path):
        assert not is_credentials_file(path)


class TestTrustT8AndT2:
    @pytest.mark.parametrize(
        "name", ["ANTHROPIC_API_KEY", "GITHUB_TOKEN", "SSH_AUTH_SOCK", "A=B", "", "1X", "my_apikey"]
    )
    def test_names_refused_in_both(self, name):
        refused(edited(BEAM, env={name: "1"}), "env")
        refused(edited(BEAM, pass_env=[name]), "pass_env[0]")

    def test_credential_words(self):
        assert {"key", "token", "secret", "auth"} <= CREDENTIAL_WORDS

    @pytest.mark.parametrize("name", ["OMP_NUM_THREADS", "LM_LICENSE_FILE", "MONKEY_COUNT", "_x"])
    def test_names_allowed(self, name):
        assert ModelSpec.from_json(edited(BEAM, env={name: "1"}, pass_env=[])).env[name] == "1"
        assert ModelSpec.from_json(edited(BEAM, pass_env=[name])).pass_env == (name,)

    def test_a_name_in_both_refused(self):
        refused(edited(BEAM, env={"LM_LICENSE_FILE": "x"}, pass_env=["LM_LICENSE_FILE"]), "LM_LICENSE_FILE")

    def test_a_pass_env_name_twice_refused(self):
        refused(edited(BEAM, pass_env=["A", "A"]), "pass_env[1]")

    def test_env_values_are_strings(self):
        refused(edited(BEAM, env={"OMP_NUM_THREADS": 4}), "env.OMP_NUM_THREADS")

    @pytest.mark.parametrize(
        ("value", "entry"),
        [("/opt/bin:$PATH", "$PATH"), ("/opt/bin:", ""), ("~/bin:/usr/bin", "~/bin"), ("bin", "bin"), ("", "")],
    )
    def test_env_path_entries(self, value, entry):
        message = refused(edited(BEAM, env={"PATH": value}), "env.PATH", "literal")
        assert repr(entry) in message

    def test_env_path_allowed(self):
        assert ModelSpec.from_json(edited(BEAM, env={"PATH": "/opt/bin:/usr/bin"})).env["PATH"] == "/opt/bin:/usr/bin"
