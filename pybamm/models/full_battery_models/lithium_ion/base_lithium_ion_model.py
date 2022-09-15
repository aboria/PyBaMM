#
# Lithium-ion base model class
#
import pybamm


class BaseModel(pybamm.BaseBatteryModel):
    """
    Overwrites default parameters from Base Model with default parameters for
    lithium-ion models

    **Extends:** :class:`pybamm.BaseBatteryModel`

    """

    def __init__(self, options=None, name="Unnamed lithium-ion model", build=False):
        super().__init__(options, name)
        self.param = pybamm.LithiumIonParameters(options)

        # Default timescale
        self._timescale = self.param.timescale

        # Set default length scales
        self._length_scales = {
            "negative electrode": self.param.L_x,
            "separator": self.param.L_x,
            "positive electrode": self.param.L_x,
            "current collector y": self.param.L_z,
            "current collector z": self.param.L_z,
        }

        for domain in ["Negative", "Positive"]:
            if self.options.electrode_types[domain.lower()] == "porous":
                domain_param = self.param.domain_params[domain]
                self.length_scales.update(
                    {
                        f"{domain} particle": domain_param.prim.R_typ,
                        f"{domain} primary particle": domain_param.prim.R_typ,
                        f"{domain} particle size": domain_param.prim.R_typ,
                    }
                )

                # Add relevant secondary length scales
                if len(self.options.phases[domain.lower()]) >= 2:
                    self._length_scales[
                        f"{domain} secondary particle"
                    ] = domain_param.sec.R_typ

        self.set_standard_output_variables()

    def set_submodels(self, build):
        self.set_external_circuit_submodel()
        self.set_porosity_submodel()
        self.set_interface_utilisation_submodel()
        self.set_crack_submodel()
        self.set_active_material_submodel()
        self.set_transport_efficiency_submodels()
        self.set_convection_submodel()
        self.set_open_circuit_potential_submodel()
        self.set_intercalation_kinetics_submodel()
        self.set_particle_submodel()
        self.set_solid_submodel()
        self.set_electrolyte_submodel()
        self.set_thermal_submodel()
        self.set_current_collector_submodel()

        self.set_sei_submodel()
        self.set_lithium_plating_submodel()
        self.set_total_interface_submodel()

        if build:
            self.build_model()

    @property
    def default_parameter_values(self):
        if self.whole_cell_domains == [
            "negative electrode",
            "separator",
            "positive electrode",
        ]:
            return pybamm.ParameterValues("Marquis2019")
        else:
            return pybamm.ParameterValues("Xu2019")

    @property
    def default_quick_plot_variables(self):
        if self.whole_cell_domains == ["separator", "positive electrode"]:
            return [
                "Electrolyte concentration [mol.m-3]",
                "Positive particle surface concentration [mol.m-3]",
                "Current [A]",
                "Electrolyte potential [V]",
                "Positive electrode potential [V]",
                "Terminal voltage [V]",
            ]
        else:
            return [
                "Negative particle surface concentration [mol.m-3]",
                "Electrolyte concentration [mol.m-3]",
                "Positive particle surface concentration [mol.m-3]",
                "Current [A]",
                "Negative electrode potential [V]",
                "Electrolyte potential [V]",
                "Positive electrode potential [V]",
                "Terminal voltage [V]",
            ]

    def set_standard_output_variables(self):
        super().set_standard_output_variables()

        # Particle concentration position
        var = pybamm.standard_spatial_vars
        if self.options.electrode_types["negative"] == "porous":
            self.variables.update(
                {"r_n": var.r_n, "r_n [m]": var.r_n * self.param.n.prim.R_typ}
            )
        if self.options.electrode_types["positive"] == "porous":
            self.variables.update(
                {"r_p": var.r_p, "r_p [m]": var.r_p * self.param.p.prim.R_typ}
            )

    def set_degradation_variables(self):
        """Sets variables that quantify degradation (LAM, LLI, etc)"""
        param = self.param

        domains = [d for d in self.options.whole_cell_domains if d != "Separator"]
        for Domain in domains:
            domain = Domain.lower()
            self.variables[f"Total lithium in {domain} [mol]"] = sum(
                self.variables[f"Total lithium in {phase} phase in {domain} [mol]"]
                for phase in self.options.phases[domain.split()[0]]
            )

            # LAM
            C_k = self.variables[f"{Domain} capacity [A.h]"]
            n_Li_k = self.variables[f"Total lithium in {domain} [mol]"]
            domain_param = getattr(self.param, domain[0])  # param.n or param.p
            LAM_k = (1 - C_k / domain_param.cap_init) * 100
            self.variables.update(
                {
                    f"LAM_{domain[0]}e [%]": LAM_k,
                    f"Loss of active material in {domain} [%]": LAM_k,
                }
            )

        # LLI
        n_Li_e = self.variables["Total lithium in electrolyte [mol]"]
        n_Li_particles = sum(
            self.variables[f"Total lithium in {domain.lower()} [mol]"]
            for domain in domains
        )
        n_Li = n_Li_particles + n_Li_e

        # LLI is usually defined based only on the percentage lithium lost from
        # particles
        LLI = (1 - n_Li_particles / param.n_Li_particles_init) * 100
        LLI_tot = (1 - n_Li / param.n_Li_init) * 100

        self.variables.update(
            {
                "LLI [%]": LLI,
                "Loss of lithium inventory [%]": LLI,
                "Loss of lithium inventory, including electrolyte [%]": LLI_tot,
                # Total lithium
                "Total lithium [mol]": n_Li,
                "Total lithium in particles [mol]": n_Li_particles,
                # Lithium lost
                "Total lithium lost [mol]": param.n_Li_init - n_Li,
                "Total lithium lost from particles [mol]": param.n_Li_particles_init
                - n_Li_particles,
                "Total lithium lost from electrolyte [mol]": param.n_Li_e_init - n_Li_e,
            }
        )

        # Lithium lost to side reactions
        # Different way of measuring LLI but should give same value
        LLI_sei = self.variables["Loss of lithium to SEI [mol]"]
        LLI_reactions = LLI_sei
        if "Negative electrode" in domains:
            LLI_sei_cracks = self.variables["Loss of lithium to SEI on cracks [mol]"]
            LLI_pl = self.variables["Loss of lithium to lithium plating [mol]"]
            LLI_reactions += LLI_sei_cracks + LLI_pl

        self.variables.update(
            {
                "Total lithium lost to side reactions [mol]": LLI_reactions,
                "Total capacity lost to side reactions [A.h]": LLI_reactions
                * param.F
                / 3600,
            }
        )

    def set_summary_variables(self):
        """
        Sets the default summary variables.
        """
        summary_variables = [
            "Time [s]",
            "Time [h]",
            "Throughput capacity [A.h]",
            "Throughput energy [W.h]",
            # LAM, LLI
            "Loss of lithium inventory [%]",
            "Loss of lithium inventory, including electrolyte [%]",
            # Total lithium
            "Total lithium [mol]",
            "Total lithium in electrolyte [mol]",
            "Total lithium in particles [mol]",
            # Lithium lost
            "Total lithium lost [mol]",
            "Total lithium lost from particles [mol]",
            "Total lithium lost from electrolyte [mol]",
            "Loss of lithium to SEI [mol]",
            "Loss of capacity to SEI [A.h]",
            "Total lithium lost to side reactions [mol]",
            "Total capacity lost to side reactions [A.h]",
            # Resistance
            "Local ECM resistance [Ohm]",
        ]

        if self.options.electrode_types["negative"] == "porous":
            summary_variables += [
                "Negative electrode capacity [A.h]",
                "Loss of active material in negative electrode [%]",
                "Total lithium in negative electrode [mol]",
                "Loss of lithium to lithium plating [mol]",
                "Loss of capacity to lithium plating [A.h]",
                "Loss of lithium to SEI on cracks [mol]",
                "Loss of capacity to SEI on cracks [A.h]",
            ]
        if self.options.electrode_types["positive"] == "porous":
            summary_variables += [
                "Positive electrode capacity [A.h]",
                "Loss of active material in positive electrode [%]",
                "Total lithium in positive electrode [mol]",
            ]

        self.summary_variables = summary_variables

    def set_open_circuit_potential_submodel(self):
        for domain in ["negative", "positive"]:
            domain_options = getattr(self.options, domain)
            for phase in self.options.phases[domain]:
                ocp_option = getattr(domain_options, phase)["open circuit potential"]
                ocp_submodels = pybamm.open_circuit_potential
                if ocp_option == "single":
                    ocp_model = ocp_submodels.SingleOpenCircuitPotential
                elif ocp_option == "current sigmoid":
                    ocp_model = ocp_submodels.CurrentSigmoidOpenCircuitPotential
                self.submodels[f"{domain} {phase} open circuit potential"] = ocp_model(
                    self.param, domain, "lithium-ion main", self.options, phase
                )

    def set_sei_submodel(self):
        if self.options.electrode_types["negative"] == "planar":
            reaction_loc = "interface"
        elif self.options["x-average side reactions"] == "true":
            reaction_loc = "x-average"
        else:
            reaction_loc = "full electrode"

        if self.options["SEI"] == "none":
            self.submodels["sei"] = pybamm.sei.NoSEI(self.param, self.options)
        elif self.options["SEI"] == "constant":
            self.submodels["sei"] = pybamm.sei.ConstantSEI(self.param, self.options)
        else:
            self.submodels["sei"] = pybamm.sei.SEIGrowth(
                self.param, reaction_loc, self.options, cracks=False
            )
        # Do not set "sei on cracks" submodel for half-cells
        # For full cells, "sei on cracks" submodel must be set, even if it is zero
        if reaction_loc != "interface":
            if (
                self.options["SEI"] in ["none", "constant"]
                or self.options["SEI on cracks"] == "false"
            ):
                self.submodels["sei on cracks"] = pybamm.sei.NoSEI(
                    self.param, self.options, cracks=True
                )
            else:
                self.submodels["sei on cracks"] = pybamm.sei.SEIGrowth(
                    self.param, reaction_loc, self.options, cracks=True
                )

    def set_lithium_plating_submodel(self):
        if self.options["lithium plating"] == "none":
            self.submodels["lithium plating"] = pybamm.lithium_plating.NoPlating(
                self.param, self.options
            )
        else:
            x_average = self.options["x-average side reactions"] == "true"
            self.submodels["lithium plating"] = pybamm.lithium_plating.Plating(
                self.param, x_average, self.options
            )

    def set_total_interface_submodel(self):
        self.submodels["total interface"] = pybamm.interface.TotalInterfacialCurrent(
            self.param, "lithium-ion", self.options
        )

    def set_crack_submodel(self):
        for domain in ["Negative", "Positive"]:
            crack = getattr(self.options, domain.lower())["particle mechanics"]
            if crack == "none":
                self.submodels[
                    domain.lower() + " particle mechanics"
                ] = pybamm.particle_mechanics.NoMechanics(
                    self.param, domain, options=self.options, phase="primary"
                )
            elif crack == "swelling only":
                self.submodels[
                    domain.lower() + " particle mechanics"
                ] = pybamm.particle_mechanics.SwellingOnly(
                    self.param, domain, options=self.options, phase="primary"
                )
            elif crack == "swelling and cracking":
                self.submodels[
                    domain.lower() + " particle mechanics"
                ] = pybamm.particle_mechanics.CrackPropagation(
                    self.param,
                    domain,
                    self.x_average,
                    options=self.options,
                    phase="primary",
                )

    def set_active_material_submodel(self):
        for domain in ["negative", "positive"]:
            if self.options.electrode_types[domain] == "porous":
                lam = getattr(self.options, domain)["loss of active material"]
                phases = self.options.phases[domain]
                for phase in phases:
                    if lam == "none":
                        submod = pybamm.active_material.Constant(
                            self.param, domain, self.options, phase
                        )
                    else:
                        submod = pybamm.active_material.LossActiveMaterial(
                            self.param, domain, self.options, self.x_average
                        )
                    self.submodels[f"{domain} {phase} active material"] = submod

                # Submodel for the total active material, summing up each phase
                if len(phases) > 1:
                    self.submodels[
                        f"{domain} total active material"
                    ] = pybamm.active_material.Total(self.param, domain, self.options)

    def set_porosity_submodel(self):
        if (
            self.options["SEI porosity change"] == "false"
            and self.options["lithium plating porosity change"] == "false"
        ):
            self.submodels["porosity"] = pybamm.porosity.Constant(
                self.param, self.options
            )
        elif (
            self.options["SEI porosity change"] == "true"
            or self.options["lithium plating porosity change"] == "true"
        ):
            x_average = self.options["x-average side reactions"] == "true"
            self.submodels["porosity"] = pybamm.porosity.ReactionDriven(
                self.param, self.options, x_average
            )
