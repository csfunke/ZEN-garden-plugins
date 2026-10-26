import linopy as lp
import numpy as np
import xarray as xr
from zen_garden.model.component_types.constraint import GenericConstraint
from zen_garden.model.registries.multi_index_helper import MultiIndexHelper


class NetImportConstraint(GenericConstraint):

    @classmethod
    def build(cls, model_constructor):
        """Limit inbound, outbound, and net carrier imports for each node.

        .. math::
            \\sum_{t\\in\\mathcal{T}}\\tau_t\\left(
            \\sum_{j\\in\\mathcal{J}}\\sum_{e\\in\\underline{\\mathcal{E}}}
            (F_{j,e,t}-F^\\mathrm{l}_{j,e,t}) + F^\\mathrm{imp}_{c,n,t}
            \\right)
            \\leq b^\\mathrm{in}_{c,n,y} \n

            \\sum_{t\\in\\mathcal{T}}\\tau_t\\left(
            \\sum_{j\\in\\mathcal{J}}\\sum_{e'\\in\\overline{\\mathcal{E}}}
            F_{j,e',t} + F^\\mathrm{exp}_{c,n,t}
            \\right)
            \\leq b^\\mathrm{out}_{c,n,y}

        The net limit applies to total inbound flow minus total outbound flow.
        :math:`F_{j,e,t}` is the transported flow of carrier :math:`c` on ingoing
        edges :math:`e` minus the losses :math:`F^\\mathrm{l}_{j,e,t}` of all
        transport technologies :math:`j` at time step :math:`t`\n
        :math:`F_{j,e',t}`: transported flow of carrier :math:`c` on outgoing
        edges :math:`e'` at time step :math:`t`\n
        :math:`b^\\mathrm{in}_{c,n,y}`: transport limit into the node :math:`n`
        of carrier :math:`c` in year :math:`y` \n
        :math:`b^\\mathrm{out}_{c,n,y}`: transport limit out of the node
        :math:`n` of carrier :math:`c` in year :math:`y`\n
        """
        ### index sets
        index_values, index_names = (
            model_constructor.optimization_model.create_custom_set(
                ["set_carriers", "set_nodes", "set_time_steps_operation"]
            )
        )
        index = MultiIndexHelper(index_values, index_names)

        # carrier flow transport technologies
        if model_constructor.optimization_model.variables["flow_transport"].size > 0:
            # recalculate all the edges
            edges_in = {
                node: model_constructor.network_topology.calculate_connected_edges(
                    node, "in"
                )
                for node in model_constructor.optimization_model.sets["set_nodes"]
            }
            edges_out = {
                node: model_constructor.network_topology.calculate_connected_edges(
                    node, "out"
                )
                for node in model_constructor.optimization_model.sets["set_nodes"]
            }
            max_edges = max(
                [
                    len(edges_in[node])
                    for node in model_constructor.optimization_model.sets["set_nodes"]
                ]
                + [
                    len(edges_out[node])
                    for node in model_constructor.optimization_model.sets["set_nodes"]
                ]
            )

            # create the variables
            flow_transport_in_vars = xr.DataArray(
                -1,
                coords=[
                    model_constructor.optimization_model.parameters.demand.coords[
                        "set_carriers"
                    ],
                    model_constructor.optimization_model.parameters.demand.coords[
                        "set_nodes"
                    ],
                    model_constructor.optimization_model.parameters.demand.coords[
                        "set_time_steps_operation"
                    ],
                    xr.DataArray(
                        np.arange(
                            len(
                                model_constructor.optimization_model.sets[
                                    "set_transport_technologies"
                                ]
                            )
                            * (2 * max_edges + 1)
                        ),
                        dims=["_term"],
                    ),
                ],
            )
            flow_transport_in_coeffs = xr.full_like(
                flow_transport_in_vars, np.nan, dtype=float
            )
            flow_transport_out_vars = flow_transport_in_vars.copy()
            flow_transport_out_coeffs = xr.full_like(
                flow_transport_in_vars, np.nan, dtype=float
            )
            for carrier, node in index.get_unique([0, 1]):
                techs = [
                    tech
                    for tech in model_constructor.optimization_model.sets[
                        "set_transport_technologies"
                    ]
                    if carrier
                    in model_constructor.optimization_model.sets[
                        "set_reference_carriers"
                    ][tech]
                ]
                edges_in = model_constructor.network_topology.calculate_connected_edges(
                    node, "in"
                )
                edges_out = (
                    model_constructor.network_topology.calculate_connected_edges(
                        node, "out"
                    )
                )

                # get the variables for the in flow
                in_vars_plus = (
                    model_constructor.optimization_model.variables["flow_transport"]
                    .labels.loc[techs, edges_in, :]
                    .data
                )
                in_vars_plus = in_vars_plus.reshape((-1, in_vars_plus.shape[-1])).T
                in_coefs_plus = np.ones_like(in_vars_plus)
                in_vars_minus = (
                    model_constructor.optimization_model.variables[
                        "flow_transport_loss"
                    ]
                    .labels.loc[techs, edges_in, :]
                    .data
                )
                in_vars_minus = in_vars_minus.reshape((-1, in_vars_minus.shape[-1])).T
                in_coefs_minus = np.ones_like(in_vars_minus)
                in_vars = np.concatenate([in_vars_plus, in_vars_minus], axis=1)
                in_coefs = np.concatenate([in_coefs_plus, -in_coefs_minus], axis=1)
                flow_transport_in_vars.loc[
                    carrier, node, :, : in_vars.shape[-1] - 1
                ] = in_vars
                flow_transport_in_coeffs.loc[
                    carrier, node, :, : in_coefs.shape[-1] - 1
                ] = in_coefs

                # get the variables for the out flow
                out_vars_plus = (
                    model_constructor.optimization_model.variables["flow_transport"]
                    .labels.loc[techs, edges_out, :]
                    .data
                )
                out_vars_plus = out_vars_plus.reshape((-1, out_vars_plus.shape[-1])).T
                out_coefs_plus = np.ones_like(out_vars_plus)
                flow_transport_out_vars.loc[
                    carrier, node, :, : out_vars_plus.shape[-1] - 1
                ] = out_vars_plus
                flow_transport_out_coeffs.loc[
                    carrier, node, :, : out_coefs_plus.shape[-1] - 1
                ] = out_coefs_plus

            # craete the linear expression
            term_flow_transport_in = lp.LinearExpression(
                xr.Dataset(
                    {"coeffs": flow_transport_in_coeffs, "vars": flow_transport_in_vars}
                ),
                model_constructor.optimization_model.lp_model,
            )
            term_flow_transport_out = lp.LinearExpression(
                xr.Dataset(
                    {
                        "coeffs": flow_transport_out_coeffs,
                        "vars": flow_transport_out_vars,
                    }
                ),
                model_constructor.optimization_model.lp_model,
            )
        else:
            # if there is no carrier flow we just create empty arrays
            term_flow_transport_in = (
                model_constructor.optimization_model.variables["flow_import"]
                .where(False)
                .to_linexpr()
            )
            term_flow_transport_out = (
                model_constructor.optimization_model.variables["flow_import"]
                .where(False)
                .to_linexpr()
            )

        # Direct carrier imports and exports at each node.
        term_carrier_import = model_constructor.optimization_model.variables[
            "flow_import"
        ].to_linexpr()
        term_carrier_export = model_constructor.optimization_model.variables[
            "flow_export"
        ].to_linexpr()
        # sum up over all operation time steps per year
        time_step_duration = cls.get_year_time_step_duration_array(model_constructor)
        term_flow_transport_in = (
            term_flow_transport_in.assign_coords(time_step_duration.coords)
            * time_step_duration
        ).sum("set_time_steps_operation")
        term_flow_transport_out = (
            term_flow_transport_out.assign_coords(time_step_duration.coords)
            * time_step_duration
        ).sum("set_time_steps_operation")
        term_carrier_import = (
            term_carrier_import.assign_coords(time_step_duration.coords)
            * time_step_duration
        ).sum("set_time_steps_operation")
        term_carrier_export = (
            term_carrier_export.assign_coords(time_step_duration.coords)
            * time_step_duration
        ).sum("set_time_steps_operation")

        term_flow_import_total = term_flow_transport_in + term_carrier_import
        term_flow_export_total = term_flow_transport_out + term_carrier_export
        term_flow_import_net = term_flow_import_total - term_flow_export_total

        # transport limits
        transport_limit_in = (
            model_constructor.optimization_model.parameters.transport_limit_in
        )
        transport_limit_out = (
            model_constructor.optimization_model.parameters.transport_limit_out
        )
        transport_limit_net = (
            model_constructor.optimization_model.parameters.transport_limit_net
        )
        mask_limit_in = transport_limit_in != np.inf
        mask_limit_out = transport_limit_out != np.inf
        mask_limit_net = transport_limit_net != np.inf
        # create the constraints
        lhs_in = term_flow_import_total.where(mask_limit_in)
        lhs_out = term_flow_export_total.where(mask_limit_out)
        lhs_net = term_flow_import_net.where(mask_limit_net)
        rhs_in = transport_limit_in.where(mask_limit_in, 0.0)
        rhs_out = transport_limit_out.where(mask_limit_out, 0.0)
        rhs_net = transport_limit_net.where(mask_limit_net, 0.0)
        constraints_in = lhs_in <= rhs_in
        constraints_out = lhs_out <= rhs_out
        constraints_net = lhs_net <= rhs_net
        # add the constraints to the model
        cls.add_constraint(
            model_constructor, "constraint_transport_limit_in", constraints_in
        )
        cls.add_constraint(
            model_constructor, "constraint_transport_limit_out", constraints_out
        )
        cls.add_constraint(
            model_constructor, "constraint_transport_limit_net", constraints_net
        )
