'''
Created on May 23, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''

import argparse 
from amaranth.cli import main_parser, main_runner

_CLISingleton = None 

import logging 
log = logging.getLogger(__name__)


class CLI:
    
    @classmethod 
    def get(cls):
        global _CLISingleton
        if _CLISingleton is None:
            log.info("Creating CLI singleton")
            _CLISingleton = cls()
            log.debug(f"FORMAL {_CLISingleton.verify}")
        
        return _CLISingleton
            
    
    def __init__(self):
        self.parser = main_parser()
        p_action = self.parser._actions[1] # this is really ugly, no other way to access the SubParsersAction?
        
        p_verify = p_action.add_parser("verify",
                                       help="generate including verifications")
        p_verify.add_argument('-c', '--cover', dest="verify_cover", default=False, action="store_true", 
                              help="include (guarded) cover statements [False]")
        p_verify.add_argument('-t', metavar="TYPE", dest="verify_outputtype", type=str, default='il', 
                              help="type of output to generate il, v or cc [il]")
        p_verify.add_argument('-d', '--depthprobe', dest="verify_depth", default=False, action="store_true", 
                              help="enable depth-probe covers [False]")
        p_verify.add_argument('-g', '--groups', metavar="VERIFGROUPS", dest="verify_groups", type=str, default='', 
                              help="enable only verifications in these groups (comma,sep,list)")
        
        p_verify.add_argument("generate_file",
                              metavar="FILE", type=argparse.FileType("w"), nargs="?",
                              help="write generated code to FILE")
        
        
        
        
        
        
        p_sim = p_action.add_parser("sim",
                                       help="run simulations")
        p_sim.add_argument('-g', '--groups', metavar="SIMGROUPS", dest="verify_groups", type=str, default='', 
                            help="enable only simulations in these groups (comma,sep,list)")
        
        
        p_sim.add_argument("-p", "--period", dest="sync_period",
            metavar="TIME", type=float, default=1e-6,
            help="set 'sync' clock domain period to TIME (default: %(default)s)")
        p_sim.add_argument("-c", "--clocks", dest="sync_clocks",
            metavar="COUNT", type=int, required=False, default=0,
            help="simulate for COUNT 'sync' clock periods")
        
        
        
        
        
        self.args = self.parser.parse_args()
        self.verifyEnabled = False
        
        
    @property 
    def action(self):
        if 'action' in self.args:
            return self.args.action 
        
        return None
    
    
    @property 
    def generate(self):
        return self.action and self.action == 'generate' 
        
    
    @property
    def simulate(self):
        return self.action and (self.action == 'sim' or self.action == 'simulate' )
    
    @property 
    def verify(self):
        # we mess about with the action so have a cache for verifyEnabled
        if self.verifyEnabled:
            return True 
        
        if self.action and self.action == 'verify':
            self.verifyEnabled = True 
            
        return self.verifyEnabled
    
    @property 
    def enabledGroups(self):
        if 'verify_groups' not in self.args:
            return []
        
        if self.args.verify_groups is None or not len(self.args.verify_groups):
            return []
        
        return self.args.verify_groups.split(',')
    
    def groupEnabled(self, grpName:str):
        if grpName is None or not len(grpName):
            return True
        
        enabledGroups = self.enabledGroups
        if not len(enabledGroups):
            return True
        
        try:
            idx = enabledGroups.index(grpName)
        except ValueError:
            return False 
        
        return idx >= 0
        
    @property 
    def covers(self):
        return self.verify and self.args.verify_cover
    
    @property 
    def depthProbe(self):
        return self.verify and self.args.verify_depth
    
    @property 
    def clock_frequency(self):
        return round(1/self.clock_period)
    
    @property 
    def clock_period(self):
        if not self.simulate:
            return 1e-6
        return self.args.sync_period
    
    
    @property
    def clocks(self):
        if not self.simulate:
            return 0 
        return self.args.sync_clocks
    
    @property 
    def simulation_runtime(self):
        return self.clock_period * self.clocks
    
    
    
    def help_string(self) -> str:
        return self.parser.format_help()
    
    def usage_string(self) -> str:
        return self.parser.format_usage()
    
    def banner_string(self) -> str:
        header = "Amaranth Testbench Runner\n"
        if self.generate:
            return f'{header}Generating design'
        if self.simulate:
            return f'{header}Simulating design'
        if self.verify:
            f'{header}Verifying design'
            
        
    
    def print_help(self):
        self.parser.print_help()
    
    def print_banner(self):
        if not self.action:
            self.print_help()
            return 
        
        
    def main(self, *args, **kwargs):
        if self.simulate:
            return 
        
        if self.verify:
            # convert this to a generate
            self.args.action = 'generate'
            self.args.generate_type = self.args.verify_outputtype
            self.args.emit_src = True
            
            
        if self.simulate:
            self.args.action = 'simulate'
            
            
        main_runner(self.parser, self.args, *args, **kwargs)
    
    
def main(*args, **kwargs):
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.history import History
    
    cli = CLI.get()
    
    if not cli.action:
        cli.print_help()
        return 
    cli.main(*args, **kwargs)
    
    if History.MaxCapacity:
        log.info(f"History in use, depths declared: [{History.MinCapacity},{History.MaxCapacity}]")
        log.warn(f"History max depth for reliable use: {History.MinCapacity}")

    unknownGroups = []
    for g in CLI.get().enabledGroups:
        if not Verification.groupKnown(g):
            if g.lower() != 'none':
                unknownGroups.append(g)
    
    if len(unknownGroups):
        log.warn(f'\nWARNING: Have specified unknown group(s): {", ".join(unknownGroups)}\nKnown:{Verification.KnownGroups.keys()}\n')
        
        
        
        