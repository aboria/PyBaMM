#
# Class for constant porosity
#
import pybamm

from .base_porosity import BaseModel


class Constant(BaseModel):
    """Submodel for constant porosity

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel


    **Extends:** :class:`pybamm.porosity.BaseModel`
    """

    def get_fundamental_variables(self):
        eps_dict = {
            domain: self.param.domain_params[domain.split()[0]].epsilon_init
            for domain in self.options.whole_cell_domains
        }
        depsdt_dict = {
            domain: pybamm.FullBroadcast(0, domain, "current collector")
            for domain in self.options.whole_cell_domains
        }

        variables = self._get_standard_porosity_variables(
            eps_dict, set_leading_order=True
        )
        variables.update(
            self._get_standard_porosity_change_variables(
                depsdt_dict, set_leading_order=True
            )
        )

        return variables

    def set_events(self, variables):
        # No events since porosity is constant
        pass
