'''
Created on Jun 29, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''

from amaranth_testbench.examples.empire import Empire
from amaranth import Module

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.asserts import Assert, Cover
    from amaranth.sim import Delay, Tick
    from amaranth_testbench.cli import CLI, main
    from amaranth_testbench.simulator import Simulator
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.history import History
    
    
    MaxStrainValue = 80
    cli = CLI.get()
    m = Module() # top level
    m.submodules.empire = dut = Empire(MaxStrainValue)
    
    
    # create a history instance and keep track 
    # off all the public signals (enable, reset and count)
    # NOTE: numStepsMax MUST be > than the check depth for this to work.
    hist = History.new(m, numCyclesToTrack=100)
    hist.trackAll(dut.ports())
    
    
        
        
    @Verification.coverAndVerify(m, dut)
    def fallAnyReasons(m:Module, emp:Empire, includeCovers:bool=False):
        if includeCovers:
            m.d.comb += Cover(hist.fell(emp.rome))
    
    @Verification.coverAndVerify(m, dut)
    def fallNotJustSlavery(m:Module, emp:Empire, includeCovers:bool=False):
        if includeCovers:
            with m.If(emp.slaveryreliance < 100):
                m.d.comb += Cover(hist.fell(emp.rome))
            
            
    @Verification.coverAndVerify(m, dut)
    def fallNotGov(m:Module, emp:Empire, includeCovers:bool=False):
        
        # use isNever to force the case where neither corruption 
        # nor overspending goes high for the first 90 cycles
        if includeCovers:
            with m.If(hist.isNever(emp.corruption, 1, 0, 90)):
                with m.If(hist.isNever(emp.overspending, 1, 0, 90)):
                    m.d.comb += Cover(hist.fell(emp.rome))
                    
            # since these are 1 bit signals, the above 
            # implies that both were a constant '0' the whole time
            # so is entirely equivalent to
            with m.If(hist.isConstant(emp.corruption, 0, 0, 90)):
                with m.If(hist.isConstant(emp.overspending, 0, 0, 90)):
                    m.d.comb += Cover(hist.fell(emp.rome))
            
                    
    
    @Verification.coverAndVerify(m, dut)
    def verifyStrain(m:Module, emp:Empire, includeCovers:bool=False):
        with m.If(
                hist.pastFell(emp.borderintegrety) 
                & hist.pastRose(emp.corruption) 
                & hist.pastRose(emp.overspending)):
            
            m.d.comb += Assert(emp.strain >= 23)
            
            @Verification.depthProbe
            def dp(): # only active with --depthprobe
                m.d.comb += Cover(emp.strain == 24)
                
    @Verification.coverAndVerify(m, dut)
    def verifyFall(m:Module, emp:Empire, includeCovers:bool=False):
        with m.If(hist.fell(emp.rome)):
            m.d.comb += Assert(emp.strain >= MaxStrainValue)
        
    
        
    @Simulator.simulate(m, 'war', traces=dut.ports())
    def warEffect():
        yield dut.war.eq(1)
        yield Delay(50e-6)
        
        
    @Simulator.simulate(m, 'internal_awful', traces=dut.ports())
    def slaveryAndCorruptionEffect():
        for i in range(0, 150):
            yield dut.slaveryreliance.eq(i)
            yield dut.corruption.eq(i % 3)
            yield dut.overspending.eq(i % 2)
            yield Tick()
        
    
    main(m, ports=dut.ports())
