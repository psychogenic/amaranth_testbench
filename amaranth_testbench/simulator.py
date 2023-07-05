'''
Created on Feb 27, 2023

Convenience functions for running simulations.

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

from amaranth_testbench.cli import CLI
from amaranth_testbench.verification import Verification
from amaranth import Module
from amaranth.sim import Simulator as AmaranthSimulator
from amaranth.sim import Delay, Settle, Tick

class Simulator:
    Verbose = True
    @staticmethod
    def simulate(m:Module, baseName:str, traces=[], clockFreq:int=None, runTimeSecs:float=None, group=None):
        
        Verification.addKnownGroup(group)
        
        def wrapper(fn):
            if not CLI.get().simulate:
                # not even simulating, forget about it
                return 
            
            if group is None or CLI.get().groupEnabled(group):
                Simulator.run(m, baseName, traces=traces, processes=[fn], clockFreq=clockFreq, runTimeSecs=runTimeSecs)
                    
        return wrapper

    @classmethod
    def run(cls, m:Module, baseFileName:str, traces=[], processes=[], clockFreq:int=None, runTimeSecs:float=None):
        if clockFreq is None:
            clockFreq = CLI.get().clock_frequency
            
        s = cls.getSimulator(m, clockFreq)
        if processes is not None and len(processes):
            for p in processes:
                if Simulator.Verbose:
                    print ("Adding process %s" % str(p))
                s.add_process(p)
        
        cls.doSimulation(s, baseFileName, runTimeSecs, traces)
    
    @classmethod
    def getSimulator(cls, m:Module, clockFreq:int=None) -> AmaranthSimulator:
        if clockFreq is None:
            clockFreq = CLI.get().clock_frequency
        sim = AmaranthSimulator(m)
        if Simulator.Verbose:
            print(f"Adding clock @ {clockFreq}Hz")
        sim.add_clock(1/clockFreq, domain="sync")
        return sim
        
    @classmethod
    def doSimulation(cls, sim:AmaranthSimulator, baseFileName:str, runTimeSecs:float=None, traces=[]):
        if Simulator.Verbose:
            print(f"Running {baseFileName} simulation")
        # sim.add_process(process) # or sim.add_sync_process(process), see below
        with sim.write_vcd(f"{baseFileName}.vcd", f"{baseFileName}.gtkw", traces=traces
                           ):
            # sim.run_until(runTimeSecs, run_passive=True)
            if runTimeSecs is not None:
                print(f"RUN UNTIL {runTimeSecs}")
                sim.run_until(runTimeSecs, run_passive=True)
            else:
                print("RUN FOREVER")
                sim.run()
        
        if Simulator.Verbose:
            print("Done!")
            print(f"gtkwave {baseFileName}.gtkw to see results!")
    
    
    @classmethod 
    def set(cls, signal, value):
        yield signal.eq(value)
        
    @classmethod 
    def setAndTick(cls, signal, value):
        yield signal.eq(value)
        yield Tick()
         
    @classmethod 
    def perform(cls, action):
        yield action 
        
    @classmethod 
    def performAndTick(cls, action):
        yield action
        yield Tick()