'''
Created on Jun 29, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''
from amaranth_testbench.examples.counter import BasicCounter
from amaranth import Signal, Module
from amaranth import ResetSignal # ClockDomain, ClockSignal, 

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.asserts import Assert, Cover, Assume
    from amaranth.sim import Delay
    from amaranth_testbench.cli import CLI, main
    from amaranth_testbench.simulator import Simulator
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.history import History
    
    
    MaxCyclesToTrack = 60
    MaxCountValue = 16
    cli = CLI.get()
    cli.print_banner()
    
    
    m = Module() # top level
    m.submodules.counter = dut = BasicCounter(MaxCountValue)
    
    
    # create a history instance and keep track 
    # off all the public signals (enable, reset and count)
    # NOTE: numCyclesToTrack MUST be > than the check depth for this to work.
    hist = History.new(m, numCyclesToTrack=MaxCyclesToTrack)
    hist.trackAll(dut.ports())
    
    rst = Signal()
    m.d.comb += ResetSignal().eq(rst)
    
    hist.track(rst)
    
        
    @Simulator.simulate(m, 'count_up_basic', traces=dut.ports())
    def countUp():
        yield Delay((4 + (MaxCountValue*2))*1e-6)
        
        
    @Verification.coverAndVerify(m, dut)
    def noOverflow(m:Module, counter:BasicCounter, includeCovers:bool=False):
        # no matter what, counter never exceeds max
        m.d.comb += Assert(counter.count <= counter.max)
    
        
    @Verification.coverAndVerify(m, dut)
    def pastHistoryChecks(m:Module, counter:BasicCounter, includeCovers:bool=False):
        
        # check that the past is always the current count - 1
        # except when we start or loop over
        with m.If(hist.started & (counter.count > 0)):
            m.d.comb += Assert(hist.past(counter.count) == (counter.count - 1))
            @Verification.depthProbe
            def dp(): # only active with --depthprobe
                m.d.comb += Cover(hist.past(counter.count) == (counter.count - 1))
        
        # check that we've looped over as expected 
        # this is true every time count is 0, except the first
        # so we use the history tick count to ensure it isn't startup
        with m.If(hist.started & (counter.count == 0)):
            m.d.comb += Assert(hist.past(counter.count) == MaxCountValue)
            
            @Verification.depthProbe
            def dp2(): # only active with --depthprobe
                m.d.comb += Cover(hist.past(counter.count) == MaxCountValue)
            
        
        if includeCovers:
            with m.If(hist.isEver(counter.count, 8, numCycles=10)):
                # since it was 8 at least once before, will force it 
                # to loop over to the next one (at least)
                m.d.comb += Cover(counter.count == 8) 
                #m.d.comb += Assert(hist.cyclespassed[7])
                
            # another way to force it to run for a while
            with m.If(hist.cycle > 20):
                m.d.comb += Cover(counter.count == 2)
                
                
            m.d.comb += Cover(hist.cycle == MaxCyclesToTrack - 2)
    
    main(m, ports=dut.ports())




    

        