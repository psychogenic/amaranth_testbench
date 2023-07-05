'''
Created on Jun 30, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''


from amaranth import Module, Signal
from amaranth.asserts import Cover, Assert

from amaranth_testbench.examples.ferryman import FerryManProblem

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth_testbench.cli import main
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.simulator import Simulator, Tick, Delay
    from amaranth_testbench.history import History

        
    m = Module() # top level
    m.submodules.fman = dut = FerryManProblem()
    
    hist = History.new(m, numCyclesToTrack=25)
    hist.trackAll(dut.ports())    
        
    @Verification.coverAndVerify(m, dut)
    def solveFerrymanProblemWithCover(m:Module, f:FerryManProblem, includeCovers:bool=False):
        
        # we want to look at history/valueAts/past of various signals
        # so create a history object
        
            
        m.d.comb += Cover(
                                    # the goal to satisfy: everyone on other side *without fail*
                                    f.cabbage & f.goat & f.wolf & f.ferryman & ~f.failure
                                    
                                # hold first step with ferryman on start shore, for clarity
                                # & (hist.valueAt(f.ferryman, 0) == 0) 
                                # & (hist.cycle > 0)
                        )
        
        m.d.comb += Cover(
                                # the goal to satisfy: everyone on other side *without fail*
                                f.cabbage & f.goat & f.wolf & f.ferryman & ~f.failure
                                & 
                                # wolf has been here for at least 1 clock
                                hist.past(f.wolf) 
                                &
                                # goat has been here for at least 1 clock
                                hist.past(f.goat) 
                                & 
                                # cabbage has been here for at least 1 clock
                                hist.past(f.cabbage) 
                                &
                                # hold first step with ferryman on start shore, for clarity
                                (hist.valueAt(f.ferryman, 0) == 0) 
                        )
        
        
        
        
    @Verification.coverAndVerify(m, dut)
    def verifyModuleFunction(m:Module, f:FerryManProblem, includeCovers:bool=False):
        
        
        with m.If(
                 (hist.past(f.cabbage) == hist.past(f.goat))
                &
                 (hist.past(f.ferryman) != hist.past(f.cabbage)) 
                
            ):
            m.d.sync += Assert(f.failure)
            
            
        with m.If(
                 (hist.past(f.wolf) == hist.past(f.goat))
                &
                 (hist.past(f.ferryman) != hist.past(f.goat)) 
                
            ):
            m.d.sync += Assert(f.failure)
            
            
        
        
    def transport(item:Signal, side:int=1):
        yield dut.ferryman.eq(side)
        yield item.eq(side)
        yield Tick()
        
    def moveFerryman(side:int):
        yield dut.ferryman.eq(side)
        yield Tick()
        
    def startSimWait():
        yield Delay(2e-6)  
    
        
    def endSimWait():
        yield Delay(2e-6)   
         
    # all the ways we should fail
    
    @Simulator.simulate(m, 'ferryfail_leftalone', traces=dut.ports(), group='failuremode')
    def failLeaveUnmonitored():
        # leaving everyone unmonitored
        yield from startSimWait()
        yield from moveFerryman(1)
        yield from endSimWait()
    
    @Simulator.simulate(m, 'ferryfail_movenoferry', traces=dut.ports(), group='failuremode')
    def failMultimove():
        # moving magically/without ferryman
        yield from startSimWait()
        yield dut.goat.eq(1)
        yield dut.cabbage.eq(1)
        yield from endSimWait()
        
    
    @Simulator.simulate(m, 'ferryfail_multimove', traces=dut.ports(), group='failuremode')
    def failMultimove():
        # moving more than one item
        yield from startSimWait()
        yield dut.ferryman.eq(1)
        yield dut.goat.eq(1)
        yield dut.cabbage.eq(1)
        yield from endSimWait()
        
        
    @Simulator.simulate(m, 'ferryfail_cabbage_and_goat', traces=dut.ports(), group='failuremode')
    def failCabbageAndGoat():
        # leaving cabbage + goat together, alone
        yield from startSimWait()
        yield from transport(dut.goat)
        yield from moveFerryman(0)
        yield from transport(dut.cabbage)
        yield from moveFerryman(0)
        yield from endSimWait()
        
        
    @Simulator.simulate(m, 'ferryfail_goat_and_wolf', traces=dut.ports(), group='failuremode')
    def failGoatAndWolf():
        # leaving cabbage + goat together, alone
        yield from startSimWait()
        yield from transport(dut.goat)
        yield from moveFerryman(0)
        yield from transport(dut.wolf)
        yield from moveFerryman(0)
        yield from moveFerryman(1) # oops, head back!  nah, too late
        yield from endSimWait()
        
       
    
    main(m, ports=dut.ports())


